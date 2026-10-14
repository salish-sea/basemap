# Builds the basemap's archives for one area. For now that is the test window around
# Haro Strait; the whole range comes once the window looks right.
#
#   make window   every archive, in build/window/
#   make serve    a page that compares our map with Esri's

WINDOW_BBOX := -124.0,48.0,-122.2,49.2
PROTOMAPS_BUILD := 20261013

OUT := build/window
CACHE := cache
comma := ,
BBOX_WORDS := $(subst $(comma), ,$(WINDOW_BBOX))
WEST := $(word 1,$(BBOX_WORDS))
SOUTH := $(word 2,$(BBOX_WORDS))
EAST := $(word 3,$(BBOX_WORDS))
NORTH := $(word 4,$(BBOX_WORDS))

# Depths where a band starts, in metres below sea level (decision 073's tints).
BAND_LEVELS := -2000 -1000 -500 -300 -200 -150 -100 -75 -50 -30 -20 -10 -5 0
ISOBATH_LEVELS := $(filter-out 0,$(BAND_LEVELS))

# Ground between 0 m and this height is drawn as drying at low tide, wherever
# OpenStreetMap has no land over it (decisions/004). Canada's grid measures from chart
# datum, about the lowest tide; this is above the highest tides here, so the coastline,
# at high water, decides where the drying ground ends.
DRYING_TOP := 5

CRM_VOL8 := $(CACHE)/crm_vol8_2025.nc
NRCAN := $(CACHE)/nrcan_westcoast_v2_10m.tif

.PHONY: window serve clean
window: $(OUT)/protomaps.pmtiles $(OUT)/osm.pmtiles $(OUT)/depth.pmtiles $(OUT)/elevation.pmtiles

serve: window
	pnpm run serve

clean:
	rm -rf $(OUT)

$(CRM_VOL8):
	mkdir -p $(CACHE)
	curl -sSfL -o $@.part https://www.ngdc.noaa.gov/thredds/fileServer/crm/cudem/crm_vol8_2025.nc
	mv $@.part $@

# The 10 m GeoTIFF is compressed inside an 11 GB zip, so it can't be read in place;
# stream the zip and keep only the GeoTIFF (7.9 GB).
$(NRCAN):
	mkdir -p $(CACHE)
	curl -sSfL https://ftp.maps.canada.ca/pub/nrcan_rncan/Topography_Topographie/canada_west_coast_DEM-MNA_cote_ouest_canada/west_coast_dem_v2.zip \
	  | bsdtar -xOf - GeoTIFF/WestCoastDEM_Version2_Elevation.tif > $@.part
	mv $@.part $@

# Every output depends on this file, so a change to the window, the Protomaps build or
# the depth levels rebuilds them.
$(OUT)/protomaps.pmtiles: Makefile
	mkdir -p $(OUT)
	pmtiles extract https://build.protomaps.com/$(PROTOMAPS_BUILD).pmtiles $@ --bbox=$(WINDOW_BBOX) --maxzoom=15

# Our own layers from OpenStreetMap, kept in their own archive like the Protomaps
# extract, under the ODbL. Ferry routes: Protomaps carries them only from z12 and its
# style draws none, so they are read from the extract at z13, each way's pieces joined
# back up across tile edges, and tiled again from z6 (decisions/005). The short
# approaches to ferry berths are left out.
$(OUT)/ferries.geojsons: $(OUT)/protomaps.pmtiles Makefile
	rm -f $@
	ogr2ogr -f GeoJSONSeq $@ $< -oo ZOOM_LEVEL=13 -t_srs EPSG:4326 -dialect SQLite \
	  -sql "SELECT MAX(name) AS name, MAX(network) AS network, ST_LineMerge(ST_Union(geometry)) AS geometry FROM roads WHERE kind = 'ferry' AND COALESCE(name, '') NOT LIKE '%Approach' GROUP BY mvt_id"

# Routes that share a channel are drawn as one line up to z12 (scripts/ferries.py).
# The script writes both files; macOS's make (3.81) has no rule for two outputs at once.
$(OUT)/ferry_channels.geojsons: $(OUT)/ferries.geojsons scripts/ferries.py Makefile
	uv run -q scripts/ferries.py $< $@ $(OUT)/ferry_routes.geojsons

$(OUT)/ferry_routes.geojsons: $(OUT)/ferry_channels.geojsons ;

$(OUT)/osm.pmtiles: $(OUT)/ferry_channels.geojsons $(OUT)/ferry_routes.geojsons Makefile
	tippecanoe -q --force -o $@ -Z6 -z14 --no-feature-limit --no-tile-size-limit \
	  --attribution="© OpenStreetMap contributors" \
	  -L ferries:$(OUT)/ferry_channels.geojsons -L ferry_routes:$(OUT)/ferry_routes.geojsons

# One 30 m grid (1 arc-second): NOAA's, then NRCan's, averaged from 10 m, over it
# wherever NRCan has data, which is north of about 48.06°N (decisions/001).
#
# -novshift keeps each grid's own vertical datum. Without it, gdalwarp converts NOAA's
# EGM2008 heights to heights above the ellipsoid, about 20 m lower here, because the
# target CRS has no vertical datum. NRCan's grid is to chart datum, about 1–2 m below
# NOAA's in the Salish Sea; that difference is left in (decisions/001).
$(OUT)/dem.tif: $(CRM_VOL8) $(NRCAN) Makefile
	mkdir -p $(OUT)
	gdalwarp -q -overwrite -novshift -t_srs EPSG:4326 -te $(WEST) $(SOUTH) $(EAST) $(NORTH) \
	  -tr 0.000277777777778 0.000277777777778 -r average -dstnodata -99999 \
	  -co COMPRESS=DEFLATE -co PREDICTOR=3 -co TILED=YES \
	  $(CRM_VOL8) $(NRCAN) $@

$(OUT)/bands.gpkg: $(OUT)/dem.tif
	rm -f $@
	gdal_contour -q -p -amin elev_min -amax elev_max -fl $(BAND_LEVELS) $(DRYING_TOP) $< $@

$(OUT)/bands.geojsons: $(OUT)/bands.gpkg
	ogr2ogr -f GeoJSONSeq $@ $< -dialect SQLite \
	  -sql "SELECT CAST(-elev_max AS INTEGER) AS depth, geom FROM contour WHERE elev_max <= 0"

$(OUT)/drying.geojsons: $(OUT)/bands.gpkg
	ogr2ogr -f GeoJSONSeq $@ $< -dialect SQLite \
	  -sql "SELECT geom FROM contour WHERE elev_min >= 0 AND elev_max <= $(DRYING_TOP)"

$(OUT)/isobaths.geojsons: $(OUT)/dem.tif
	rm -f $(OUT)/isobaths.gpkg
	gdal_contour -q -a elev -fl $(ISOBATH_LEVELS) $< $(OUT)/isobaths.gpkg
	ogr2ogr -f GeoJSONSeq $@ $(OUT)/isobaths.gpkg -dialect SQLite \
	  -sql "SELECT CAST(-elev AS INTEGER) AS depth, geom FROM contour"

$(OUT)/depth.pmtiles: $(OUT)/bands.geojsons $(OUT)/drying.geojsons $(OUT)/isobaths.geojsons
	tippecanoe -q --force -o $@ -Z5 -z12 \
	  --detect-shared-borders --coalesce-densest-as-needed --simplification=4 \
	  --attribution="NOAA NCEI; Natural Resources Canada" \
	  -L bands:$(OUT)/bands.geojsons -L drying:$(OUT)/drying.geojsons -L isobaths:$(OUT)/isobaths.geojsons

$(OUT)/elevation.pmtiles: $(OUT)/dem.tif scripts/elevation_tiles.py Makefile
	uv run -q scripts/elevation_tiles.py $< $@ --bbox=$(WINDOW_BBOX) --maxzoom=11
