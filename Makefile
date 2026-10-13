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

CRM_VOL8 := $(CACHE)/crm_vol8_2025.nc
NRCAN := $(CACHE)/nrcan_westcoast_v2_10m.tif

.PHONY: window serve clean
window: $(OUT)/protomaps.pmtiles $(OUT)/depth.pmtiles $(OUT)/shade.pmtiles $(OUT)/elevation.pmtiles

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

$(OUT)/protomaps.pmtiles:
	mkdir -p $(OUT)
	pmtiles extract https://build.protomaps.com/$(PROTOMAPS_BUILD).pmtiles $@ --bbox=$(WINDOW_BBOX) --maxzoom=15

# One 30 m grid (1 arc-second): NRCan's, averaged from 10 m, then NOAA's over it, which
# covers everything south of 49°N and east of 127°W.
$(OUT)/dem.tif: $(CRM_VOL8) $(NRCAN)
	mkdir -p $(OUT)
	gdalwarp -q -overwrite -t_srs EPSG:4326 -te $(WEST) $(SOUTH) $(EAST) $(NORTH) \
	  -tr 0.000277777777778 0.000277777777778 -r average -dstnodata -99999 \
	  -co COMPRESS=DEFLATE -co PREDICTOR=3 -co TILED=YES \
	  $(NRCAN) $(CRM_VOL8) $@

$(OUT)/bands.geojsons: $(OUT)/dem.tif
	rm -f $(OUT)/bands.gpkg
	gdal_contour -q -p -amin elev_min -amax elev_max -fl $(BAND_LEVELS) $< $(OUT)/bands.gpkg
	ogr2ogr -f GeoJSONSeq $@ $(OUT)/bands.gpkg -dialect SQLite \
	  -sql "SELECT CAST(-elev_max AS INTEGER) AS depth, geom FROM contour WHERE elev_max <= 0"

$(OUT)/isobaths.geojsons: $(OUT)/dem.tif
	rm -f $(OUT)/isobaths.gpkg
	gdal_contour -q -a elev -fl $(ISOBATH_LEVELS) $< $(OUT)/isobaths.gpkg
	ogr2ogr -f GeoJSONSeq $@ $(OUT)/isobaths.gpkg -dialect SQLite \
	  -sql "SELECT CAST(-elev AS INTEGER) AS depth, geom FROM contour"

$(OUT)/depth.pmtiles: $(OUT)/bands.geojsons $(OUT)/isobaths.geojsons
	tippecanoe -q --force -o $@ -Z5 -z12 \
	  --detect-shared-borders --coalesce-densest-as-needed --simplification=4 \
	  --attribution="NOAA NCEI; Natural Resources Canada" \
	  -L bands:$(OUT)/bands.geojsons -L isobaths:$(OUT)/isobaths.geojsons

$(OUT)/shade.pmtiles: $(OUT)/dem.tif scripts/raster_tiles.py
	uv run -q scripts/raster_tiles.py shade $< $@ --bbox=$(WINDOW_BBOX) --maxzoom=12

$(OUT)/elevation.pmtiles: $(OUT)/dem.tif scripts/raster_tiles.py
	uv run -q scripts/raster_tiles.py terrarium $< $@ --bbox=$(WINDOW_BBOX) --maxzoom=11
