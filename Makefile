# Builds the basemap's archives for one region, in build/<region>/:
#
#   make                  the test window around Haro Strait
#   make REGION=coast     the whole range, Monterey Bay to Haida Gwaii (a big machine:
#                         about 12 GB of source grids and 30 GB of working files)
#   make serve            a page that compares our map with Esri's, for the window
#   make pictures         the README's pictures, drawn from the region's build

REGION ?= window
# Each region's area, and the grids and names files that cover it.
ifeq ($(REGION),window)
  BBOX := -124.0,48.0,-122.2,49.2
  BASE_FILES :=
  CRM_FILES := crm_vol8_2025.nc
  GNIS_STATES := WA
else ifeq ($(REGION),coast)
  BBOX := -134.0,36.4,-121.7,54.8
  # GEBCO under everything: past 127°W, and south of 37°N past 123°W, it is the only
  # depth there is (decisions/009).
  BASE_FILES := gebco_2026_n90_w180.tif
  CRM_FILES := crm_socal_1as_vers2.nc crm_vol7_2025.nc crm_vol8_2025.nc
  GNIS_STATES := CA OR WA
else
  $(error unknown REGION '$(REGION)': use window or coast)
endif
PROTOMAPS_BUILD := 20261013

OUT := build/$(REGION)
CACHE := cache
comma := ,
BBOX_WORDS := $(subst $(comma), ,$(BBOX))
WEST := $(word 1,$(BBOX_WORDS))
SOUTH := $(word 2,$(BBOX_WORDS))
EAST := $(word 3,$(BBOX_WORDS))
NORTH := $(word 4,$(BBOX_WORDS))

# Depths where a band starts, in metres below sea level (decision 073's tints). MIN, the
# grid's lowest value, closes the deepest band: without it gdal_contour makes no polygon
# below the deepest level, and the deep ocean shows the background, the colour of 50 m.
BAND_LEVELS := MIN -2000 -1000 -500 -300 -200 -150 -100 -75 -50 -30 -20 -10 -5 0
ISOBATH_LEVELS := $(filter-out MIN 0,$(BAND_LEVELS))

# Ground between 0 m and this height is drawn as drying at low tide, wherever
# OpenStreetMap has no land over it (decisions/004). Canada's grid measures from chart
# datum, about the lowest tide; this is above the highest tides here, so the coastline,
# at high water, decides where the drying ground ends.
DRYING_TOP := 5

# NOAA's Coastal Relief Model: Southern California (31–37°N), and volumes 7 (37–44°N)
# and 8 (44–49°N), all at 1 arc-second. GEBCO's global grid, at 15 arc-seconds.
BASE := $(addprefix $(CACHE)/,$(BASE_FILES))
CRM := $(addprefix $(CACHE)/,$(CRM_FILES))
NRCAN := $(CACHE)/nrcan_westcoast_v2_10m.tif

# Marine names and the boundary at sea (decisions/006). GNIS has one file per state,
# CGNDB one for British Columbia, and NOAA's maritime limits and boundaries cover the US.
GNIS := $(foreach state,$(GNIS_STATES),$(CACHE)/gnis_$(state).txt)
CGN := $(CACHE)/cgn_bc.csv
MARITIME_BOUNDARIES := $(CACHE)/us_maritime_limits_and_boundaries.zip

# A step that fails leaves no half-written output behind for the next run to trust.
.DELETE_ON_ERROR:

.PHONY: archives assets serve pictures clean
archives: assets $(OUT)/protomaps.pmtiles $(OUT)/osm.pmtiles $(OUT)/depth.pmtiles $(OUT)/elevation.pmtiles $(OUT)/marine.pmtiles

# The labels' fonts and the icons, from Protomaps' basemaps-assets at the commit the style
# names, with the licences that come with them (decisions/010). They don't depend on the
# region, so they sit in build/assets/, where the comparison page serves them from too.
ASSETS := build/$(shell node -e "import('./style/style.ts').then((m) => process.stdout.write(m.ASSETS_PATH))")
ASSETS_COMMIT := $(shell node -e "import('./style/style.ts').then((m) => process.stdout.write(m.ASSETS_COMMIT))")
ICONS_LICENCE := https://raw.githubusercontent.com/tangrams/icons/92510779634f4a006c61ea70e50cb8c52c765a81/LICENSE.md
assets: $(ASSETS)sprites/v4/light@2x.png
$(ASSETS)sprites/v4/light@2x.png:
	rm -rf $(ASSETS) $(ASSETS:/=.part) && mkdir -p $(ASSETS:/=.part)
	curl -sSfL https://codeload.github.com/protomaps/basemaps-assets/tar.gz/$(ASSETS_COMMIT) \
	  | bsdtar -xzf - -C $(ASSETS:/=.part) --strip-components 1 '*/fonts/OFL.txt' \
	    '*/fonts/Noto Sans Regular' '*/fonts/Noto Sans Italic' '*/fonts/Noto Sans Medium' '*/sprites/v4/light*'
	curl -sSfL -o $(ASSETS:/=.part)/sprites/LICENSE.md $(ICONS_LICENCE)
	mv $(ASSETS:/=.part) $(ASSETS)

serve:
	$(MAKE) REGION=window
	pnpm run serve

# The README's pictures, drawn from the region's build as it stands; it builds nothing.
pictures:
	node scripts/pictures.ts $(REGION)

clean:
	rm -rf $(OUT)

$(CACHE)/crm_vol%_2025.nc:
	mkdir -p $(CACHE)
	curl -sSfL -o $@.part https://www.ngdc.noaa.gov/thredds/fileServer/crm/cudem/crm_vol$*_2025.nc
	mv $@.part $@

# The quarter of GEBCO's 2026 grid that holds the Americas north of the equator. The zip
# holds eight such quarters (4.2 GB) on a slow server that drops long downloads, so only
# this one is fetched, with range requests (0.5 GB; scripts/zip_member.py).
$(CACHE)/gebco_2026_n90_w180.tif:
	mkdir -p $(CACHE)
	uv run -q scripts/zip_member.py 'https://dap.ceda.ac.uk/bodc/gebco/global/gebco_2026/ice_surface_elevation/geotiff/gebco_2026_geotiff.zip?download=1' \
	  gebco_2026_n90.0_s0.0_w-180.0_e-90.0_geotiff.tif $@

$(CACHE)/crm_socal_1as_vers2.nc:
	mkdir -p $(CACHE)
	curl -sSfL -o $@.part https://www.ngdc.noaa.gov/thredds/fileServer/crm/crm_socal_1as_vers2.nc
	mv $@.part $@

# The 10 m GeoTIFF is compressed inside an 11 GB zip, so it can't be read in place;
# stream the zip and keep only the GeoTIFF (7.9 GB).
$(NRCAN):
	mkdir -p $(CACHE)
	curl -sSfL https://ftp.maps.canada.ca/pub/nrcan_rncan/Topography_Topographie/canada_west_coast_DEM-MNA_cote_ouest_canada/west_coast_dem_v2.zip \
	  | bsdtar -xOf - GeoTIFF/WestCoastDEM_Version2_Elevation.tif > $@.part
	mv $@.part $@

# The names files are updated weekly; the first copy downloaded is kept until it is
# deleted from cache/.
$(CACHE)/gnis_%.txt:
	mkdir -p $(CACHE)
	curl -sSfL https://prd-tnm.s3.amazonaws.com/StagedProducts/GeographicNames/DomesticNames/DomesticNames_$*_Text.zip \
	  | bsdtar -xOf - Text/DomesticNames_$*.txt > $@.part
	mv $@.part $@

$(CGN):
	mkdir -p $(CACHE)
	curl -sSfL https://ftp.maps.canada.ca/pub/nrcan_rncan/vector/geobase_cgn_toponyme/prov_csv_eng/cgn_bc_csv_eng.zip \
	  | bsdtar -xOf - cgn_bc_csv_eng.csv > $@.part
	mv $@.part $@

$(MARITIME_BOUNDARIES):
	mkdir -p $(CACHE)
	curl -sSfL -o $@.part https://maritimeboundaries.noaa.gov/downloads/USMaritimeLimitsAndBoundariesSHP.zip
	mv $@.part $@

# The steps that take long, or download, depend on a record of the settings they use,
# rewritten only when those change, rather than on the whole Makefile: a build machine's
# fresh copy of the Makefile is always newer than the outputs on its volume. The cheap
# steps below depend on the Makefile itself.
# Every variable a step's command reads goes in its record, or changing it rebuilds
# nothing.
PROTOMAPS_MAXZOOM := 15
ELEVATION_MAXZOOM := 11
REGION_SETTINGS := $(OUT)/region
$(REGION_SETTINGS): FORCE
	mkdir -p $(dir $@)
	@echo '$(BBOX) | $(PROTOMAPS_BUILD) to z$(PROTOMAPS_MAXZOOM) | elevation to z$(ELEVATION_MAXZOOM)' > $@.new
	@if cmp -s $@.new $@; then rm $@.new; else mv $@.new $@; fi

# Protomaps' server sometimes drops a long extract, so it is tried three times.
$(OUT)/protomaps.pmtiles: $(REGION_SETTINGS)
	for try in 1 2 3; do \
	  pmtiles extract https://build.protomaps.com/$(PROTOMAPS_BUILD).pmtiles $@.part --bbox=$(BBOX) --maxzoom=$(PROTOMAPS_MAXZOOM) && break; \
	  rm -f $@.part; sleep 30; \
	done
	mv $@.part $@

# Our own layers from OpenStreetMap, kept in their own archive like the Protomaps
# extract, under the ODbL. Ferry routes: Protomaps carries them only from z12 and its
# style draws none, so they are read from the extract at z13, each way's pieces joined
# back up across tile edges, and tiled again from z6 (decisions/005). Only named routes
# are kept: the unnamed ones here are service crossings, such as those to Mud Bay on
# Lopez, and a rail-freight barge. Protomaps doesn't carry the tags that would say so,
# so the walkways to ferry berths and the Alaska Marine Lines freight barge (tagged
# access=private in OpenStreetMap) are left out by name.
$(OUT)/ferries.geojsons: $(OUT)/protomaps.pmtiles Makefile
	rm -f $@
	ogr2ogr -f GeoJSONSeq $@ $< -oo ZOOM_LEVEL=13 -t_srs EPSG:4326 -dialect SQLite \
	  -sql "SELECT MAX(name) AS name, MAX(network) AS network, ST_LineMerge(ST_Union(geometry)) AS geometry FROM roads WHERE kind = 'ferry' AND name IS NOT NULL AND name NOT LIKE '%Approach' AND name NOT LIKE '%(Foot Access)' AND name <> 'Alaska Marine Lines' GROUP BY mvt_id"

# Routes that share a channel are drawn as one line up to z12 (scripts/ferries.py).
# The script writes both files; macOS's make (3.81) has no rule for two outputs at once.
$(OUT)/ferry_channels.geojsons: $(OUT)/ferries.geojsons scripts/ferries.py Makefile
	uv run -q scripts/ferries.py $< $@ $(OUT)/ferry_routes.geojsons

$(OUT)/ferry_routes.geojsons: $(OUT)/ferry_channels.geojsons
	@test -f $@ || { rm -f $<; $(MAKE) $<; }

$(OUT)/osm.pmtiles: $(OUT)/ferry_channels.geojsons $(OUT)/ferry_routes.geojsons Makefile
	tippecanoe -q --force -o $@ -Z6 -z14 --no-feature-limit --no-tile-size-limit \
	  --attribution="© OpenStreetMap contributors" \
	  -L ferries:$(OUT)/ferry_channels.geojsons -L ferry_routes:$(OUT)/ferry_routes.geojsons

# One 30 m grid (1 arc-second). Each source is warped to the same lattice, then
# scripts/mosaic.py lays them over one another, least preferred first, each blended in
# over 4 km at its edges: GEBCO, then NOAA's volumes, then NRCan's, which is used
# wherever it has data, north of about 48.06°N (decisions/001, 009).
#
# -novshift keeps each grid's own vertical datum. Without it, gdalwarp converts NOAA's
# EGM2008 heights to heights above the ellipsoid, about 20 m lower here, because the
# target CRS has no vertical datum. NRCan's grid is to chart datum, about 1–2 m below
# NOAA's in the Salish Sea; the blend spreads that difference out (decisions/001).
# -ot Float32, because gdalwarp would otherwise take the type of the first source, and
# NOAA's Southern California grid is in whole metres. NRCan's 10 m cells are averaged;
# GEBCO's 15-arc-second cells are interpolated.
RESAMPLING = average
GEBCO_RESAMPLING := bilinear
WARP_FLAGS := -q -overwrite -novshift -t_srs EPSG:4326 -te $(WEST) $(SOUTH) $(EAST) $(NORTH) \
  -tr 0.000277777777778 0.000277777777778 -ot Float32 -dstnodata -99999 \
  -co COMPRESS=DEFLATE -co PREDICTOR=3 -co TILED=YES -co BIGTIFF=IF_SAFER -wo NUM_THREADS=ALL_CPUS
WARP = gdalwarp $(WARP_FLAGS) -r $(RESAMPLING)

# The layers, least preferred first. NOAA's grids are one layer: they meet edge to edge,
# at 37°N and 44°N, and blending each against GEBCO at those edges would leave a strip of
# GEBCO between them (decisions/009).
LAYERS := $(if $(BASE),$(OUT)/layers/gebco.tif) $(OUT)/layers/noaa.tif $(OUT)/layers/nrcan.tif
# Kept after the build, so a change to the blend doesn't warp them all again.
.SECONDARY: $(LAYERS)

# The warps depend on this record of their settings, not on the whole Makefile, so an
# edit elsewhere in it doesn't redo them. It is rewritten only when the settings change.
WARP_SETTINGS := $(OUT)/layers/settings
$(WARP_SETTINGS): FORCE
	mkdir -p $(dir $@)
	@echo '$(WARP_FLAGS) | $(BASE) $(GEBCO_RESAMPLING) | $(CRM) $(RESAMPLING) | $(NRCAN) $(RESAMPLING)' > $@.new
	@if cmp -s $@.new $@; then rm $@.new; else mv $@.new $@; fi
.PHONY: FORCE

$(OUT)/layers/gebco.tif: RESAMPLING = $(GEBCO_RESAMPLING)
$(OUT)/layers/gebco.tif: $(BASE) $(WARP_SETTINGS)
	$(WARP) $(BASE) $@
$(OUT)/layers/noaa.tif: $(CRM) $(WARP_SETTINGS)
	$(WARP) $(CRM) $@
$(OUT)/layers/nrcan.tif: $(NRCAN) $(WARP_SETTINGS)
	$(WARP) $(NRCAN) $@

$(OUT)/dem.tif: $(LAYERS) scripts/mosaic.py
	uv run -q scripts/mosaic.py $@ $(LAYERS)

# The contours depend on this record of the levels, like the warps on theirs, so a change
# to the levels recontours but an edit elsewhere in the Makefile doesn't.
LEVELS := $(OUT)/levels
$(LEVELS): FORCE
	mkdir -p $(dir $@)
	@echo '$(BAND_LEVELS) | $(DRYING_TOP)' > $@.new
	@if cmp -s $@.new $@; then rm $@.new; else mv $@.new $@; fi

# In strips, because gdal_contour holds every polygon in memory until it finishes, which
# for the whole coast would be more than the build machine has (scripts/contour_bands.sh).
$(OUT)/bands.gpkg: $(OUT)/dem.tif $(LEVELS) scripts/contour_bands.sh
	scripts/contour_bands.sh $(OUT)/dem.tif $@ $(BAND_LEVELS) $(DRYING_TOP)

$(OUT)/bands.geojsons: $(OUT)/bands.gpkg
	ogr2ogr -f GeoJSONSeq $@ $< -dialect SQLite \
	  -sql "SELECT CAST(-elev_max AS INTEGER) AS depth, geom FROM contour WHERE elev_max <= 0"

$(OUT)/drying.geojsons: $(OUT)/bands.gpkg
	ogr2ogr -f GeoJSONSeq $@ $< -dialect SQLite \
	  -sql "SELECT geom FROM contour WHERE elev_min >= 0 AND elev_max <= $(DRYING_TOP)"

$(OUT)/isobaths.geojsons: $(OUT)/dem.tif $(LEVELS)
	rm -f $(OUT)/isobaths.gpkg
	gdal_contour -q -a elev -fl $(ISOBATH_LEVELS) $< $(OUT)/isobaths.gpkg
	ogr2ogr -f GeoJSONSeq $@ $(OUT)/isobaths.gpkg -dialect SQLite \
	  -sql "SELECT CAST(-elev AS INTEGER) AS depth, geom FROM contour"

$(OUT)/depth.pmtiles: $(OUT)/bands.geojsons $(OUT)/drying.geojsons $(OUT)/isobaths.geojsons
	tippecanoe -q --force -o $@ -Z5 -z12 \
	  --detect-shared-borders --coalesce-densest-as-needed --simplification=4 \
	  --attribution="NOAA NCEI; Natural Resources Canada; GEBCO" \
	  -L bands:$(OUT)/bands.geojsons -L drying:$(OUT)/drying.geojsons -L isobaths:$(OUT)/isobaths.geojsons

$(OUT)/elevation.pmtiles: $(OUT)/dem.tif scripts/elevation_tiles.py $(REGION_SETTINGS)
	uv run -q scripts/elevation_tiles.py $< $@ --bbox=$(BBOX) --maxzoom=$(ELEVATION_MAXZOOM)

# Which names to label, from what zoom, and at what angle (scripts/names.py), judged
# against the depth grid.
$(OUT)/names.geojsons: $(OUT)/dem.tif $(GNIS) $(CGN) scripts/names.py Makefile
	uv run -q scripts/names.py $< $@ $(addprefix --gnis=,$(GNIS)) --cgn=$(CGN) --bbox=$(BBOX)

# The boundary between Canada and the US through the water, as the two countries
# agreed it. NOAA's file also holds the US's own claims where there is no agreement,
# which are left out (decisions/006).
$(OUT)/boundary.geojsons: $(MARITIME_BOUNDARIES) Makefile
	mkdir -p $(OUT)
	rm -f $@
	ogr2ogr -f GeoJSONSeq $@ /vsizip/$</USMaritimeLimitsNBoundaries.shp -t_srs EPSG:4326 \
	  -clipdst $(WEST) $(SOUTH) $(EAST) $(NORTH) -select BOUND_ID \
	  -where "FEAT_TYPE = 'Maritime Boundary' AND NOTE LIKE 'US/Canada%' AND UNILATERAL = 0"

# Every name is kept (-r1); each leaves the tiles below its own zoom.
$(OUT)/marine.pmtiles: $(OUT)/names.geojsons $(OUT)/boundary.geojsons
	tippecanoe -q --force -o $@ -Z5 -z12 -r1 --no-feature-limit --no-tile-size-limit \
	  --attribution="USGS GNIS; Natural Resources Canada; NOAA" \
	  -L names:$(OUT)/names.geojsons -L boundary:$(OUT)/boundary.geojsons
