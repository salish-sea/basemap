# Builds the basemap's archives for one region, in build/<region>/:
#
#   make                  the test window around Haro Strait
#   make REGION=coast     the whole range, Monterey Bay to Haida Gwaii (a big machine:
#                         about 12 GB of source grids and 30 GB of working files)
#   make serve            a page that compares our map with Esri's, for the window
#   make pictures         the README's pictures, drawn from the region's build, or a VERSION
#   make images           image tiles, for pictures stitched from tiles (decisions/014);
#                         slow: about 7 tiles a second

REGION ?= window
# Each region's area, and the grids and names files that cover it.
ifeq ($(REGION),window)
  BBOX := -124.0,48.0,-122.2,49.2
  BASE_FILES :=
  CRM_FILES := crm_vol8_2025.nc
  GNIS_STATES := WA
  OSM_EXTRACTS := north-america/us/washington north-america/canada/british-columbia
else ifeq ($(REGION),coast)
  # SalishSea.io's killer whale data reaches 136–120°W and 36–54°N (decisions/011).
  BBOX := -136.0,36.0,-120.0,54.8
  # GEBCO under everything: past 127°W, and south of 37°N past 123°W, it is the only
  # depth there is (decisions/009).
  BASE_FILES := gebco_2026_n90_w180.tif
  CRM_FILES := crm_socal_1as_vers2.nc crm_vol7_2025.nc crm_vol8_2025.nc
  GNIS_STATES := CA OR WA
  OSM_EXTRACTS := north-america/us/california/norcal north-america/us/oregon north-america/us/washington \
    north-america/canada/british-columbia north-america/us/alaska
else
  $(error unknown REGION '$(REGION)': use window or coast)
endif
# Protomaps' daily build of the planet, from build.protomaps.com. Protomaps keeps only
# about a week of them, so this is moved to the newest before each version is built for
# publishing (decisions/022); a build older than that can't be extracted again.
PROTOMAPS_BUILD := 20261022

OUT := build/$(REGION)
CACHE := cache
comma := ,
BBOX_WORDS := $(subst $(comma), ,$(BBOX))
WEST := $(word 1,$(BBOX_WORDS))
SOUTH := $(word 2,$(BBOX_WORDS))
EAST := $(word 3,$(BBOX_WORDS))
NORTH := $(word 4,$(BBOX_WORDS))

# Zoomed out, and past the region's edges, the map is drawn from GEBCO's grid alone,
# coarsely, over the whole Northeast Pacific (decisions/012). Only the coast has GEBCO.
OVERVIEW_BBOX := -180.0,15.0,-90.0,70.0
OVERVIEW_RES := 0.025
# MAX closes the highest band, as MIN does the lowest: without it there is no land.
OVERVIEW_LEVELS = $(BAND_LEVELS) MAX
ifeq ($(REGION),coast)
  OVERVIEW_ARCHIVES := $(OUT)/overview.pmtiles $(OUT)/overview_elevation.pmtiles
  # Past the region's edges, the elevation tiles that straddle them are filled from the
  # coarse grid, so the relief doesn't shade a drop to sea level along the edge.
  ELEVATION_FILL := $(OUT)/overview/dem.tif
endif

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

.PHONY: archives assets fonts images places serve pictures clean
# The archives the image tiles are drawn from: all but the landmarks, which are icons and
# labels, and the shipping lanes, which only the map people pan and zoom shows (decisions/019).
IMAGE_ARCHIVES := $(OUT)/protomaps.pmtiles $(OUT)/osm.pmtiles $(OUT)/depth.pmtiles $(OUT)/elevation.pmtiles \
  $(OUT)/marine.pmtiles $(OVERVIEW_ARCHIVES)
# And the water regions, which no tile draws (decisions/027).
ARCHIVE_FILES := $(IMAGE_ARCHIVES) $(OUT)/landmarks.pmtiles $(OUT)/routes.pmtiles $(OUT)/regions.pmtiles
archives: assets fonts build/sprites/landmarks.png $(ARCHIVE_FILES)
images: $(OUT)/images/done
# The names the map labels, as lists a site can search (decisions/018).
places: $(OUT)/places-gazetteers.json $(OUT)/places-osm.json $(OUT)/places-regions.json

# The labels' fonts and the icons, from Protomaps' basemaps-assets at the commit the style
# names, with the licences that come with them (decisions/010). They don't depend on the
# region, so they sit in build/assets/, where the comparison page serves them from too.
# Make carries on when a $(shell) fails, so an empty answer stops it here rather than
# leaving ASSETS as build/ for the recipe below to delete.
ASSETS_COMMIT := $(shell node -e "import('./style/style.ts').then((m) => process.stdout.write(m.ASSETS_COMMIT))")
ASSETS_PATH := $(shell node -e "import('./style/style.ts').then((m) => process.stdout.write(m.ASSETS_PATH))")
ifeq ($(filter assets/basemaps-assets-%/,$(ASSETS_PATH)),)
  $(error could not read the assets' commit from style/style.ts; run pnpm install first)
endif
ASSETS := build/$(ASSETS_PATH)
ICONS_LICENCE := https://raw.githubusercontent.com/tangrams/icons/92510779634f4a006c61ea70e50cb8c52c765a81/LICENSE.md
assets: $(ASSETS)sprites/v4/light@2x.png
$(ASSETS)sprites/v4/light@2x.png:
	rm -rf $(ASSETS) $(ASSETS:/=.part) && mkdir -p $(ASSETS:/=.part)
	curl -sSfL https://codeload.github.com/protomaps/basemaps-assets/tar.gz/$(ASSETS_COMMIT) \
	  | bsdtar -xzf - -C $(ASSETS:/=.part) --strip-components 1 '*/fonts/OFL.txt' \
	    '*/fonts/Noto Sans Regular' '*/fonts/Noto Sans Italic' '*/fonts/Noto Sans Medium' '*/sprites/v4/light*'
	curl -sSfL -o $(ASSETS:/=.part)/sprites/LICENSE.md $(ICONS_LICENCE)
	mv $(ASSETS:/=.part) $(ASSETS)

# The labels' fonts as a published style serves them: Protomaps' three, and the depth
# labels' serif, built by scripts/serif_glyphs.sh and checked in (decisions/017). They are
# published together, because a style names one place for all its fonts. The script names
# the serif's version, so the folder is rebuilt when it changes. (The glyphs' own paths have
# spaces in them, which Make can't take as prerequisites.)
fonts: build/fonts/OFL.txt
build/fonts/OFL.txt: $(ASSETS)sprites/v4/light@2x.png scripts/serif_glyphs.sh
	rm -rf build/fonts build/fonts.part && mkdir -p build/fonts.part
	cp -R $(ASSETS)fonts/. build/fonts.part/
	cp -R style/fonts/. build/fonts.part/
	mv build/fonts.part build/fonts

serve:
	$(MAKE) REGION=window
	pnpm run serve

# The README's pictures, drawn from the region's build as it stands, or from a published
# VERSION; it builds nothing.
pictures:
	node scripts/pictures.ts $(or $(VERSION),$(REGION))

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

$(OUT)/osm.pmtiles: $(OUT)/ferry_channels.geojsons $(OUT)/ferry_routes.geojsons $(OUT)/reserves.geojsons Makefile
	tippecanoe -q --force -o $@ -Z6 -z14 --no-feature-limit --no-tile-size-limit \
	  --attribution="© OpenStreetMap contributors" \
	  -L ferries:$(OUT)/ferry_channels.geojsons -L ferry_routes:$(OUT)/ferry_routes.geojsons \
	  -L reserves:$(OUT)/reserves.geojsons

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

# The zoomed-out map: GEBCO averaged to 0.025° (about 2.5 km), cut into depth bands and
# land, split at the region's edge (scripts/overview_layers.sh), and shaded below zoom 5.
OVERVIEW_SETTINGS := $(OUT)/overview/settings
$(OVERVIEW_SETTINGS): FORCE
	mkdir -p $(dir $@)
	@echo '$(OVERVIEW_BBOX) at $(OVERVIEW_RES) | $(BBOX) | $(OVERVIEW_LEVELS) | $(BASE)' > $@.new
	@if cmp -s $@.new $@; then rm $@.new; else mv $@.new $@; fi

$(OUT)/overview/dem.tif: $(BASE) $(OVERVIEW_SETTINGS)
	gdalwarp -q -overwrite -t_srs EPSG:4326 -te $(subst $(comma), ,$(OVERVIEW_BBOX)) \
	  -tr $(OVERVIEW_RES) $(OVERVIEW_RES) -r average -ot Float32 -dstnodata -99999 \
	  -co COMPRESS=DEFLATE -co PREDICTOR=3 -co TILED=YES $(BASE) $@
$(OUT)/overview/bands.gpkg: $(OUT)/overview/dem.tif $(OVERVIEW_SETTINGS) scripts/contour_bands.sh
	scripts/contour_bands.sh $< $@ $(OVERVIEW_LEVELS)
$(OUT)/overview/sea-outside.geojsons: $(OUT)/overview/bands.gpkg $(OVERVIEW_SETTINGS) scripts/overview_layers.sh
	scripts/overview_layers.sh $< $(OUT)/overview $(BBOX) $(OVERVIEW_BBOX)
# These two take seconds, so they depend on the Makefile itself, like the other cheap steps.
$(OUT)/overview.pmtiles: $(OUT)/overview/sea-outside.geojsons Makefile
	tippecanoe -q --force -o $@ -Z0 -z5 \
	  --detect-shared-borders --coalesce-densest-as-needed --simplification=4 \
	  --attribution="GEBCO" \
	  -L bands:$(OUT)/overview/sea-outside.geojsons -L bands_zoomed_out:$(OUT)/overview/sea-inside.geojsons \
	  -L land:$(OUT)/overview/land-outside.geojsons
$(OUT)/overview_elevation.pmtiles: $(OUT)/overview/dem.tif scripts/elevation_tiles.py Makefile
	uv run -q scripts/elevation_tiles.py $< $@ --bbox=$(OVERVIEW_BBOX) --maxzoom=5

$(OUT)/elevation.pmtiles: $(OUT)/dem.tif scripts/elevation_tiles.py $(REGION_SETTINGS) $(ELEVATION_FILL)
	uv run -q scripts/elevation_tiles.py $< $@ --bbox=$(BBOX) --maxzoom=$(ELEVATION_MAXZOOM) \
	  $(if $(ELEVATION_FILL),--fill=$(ELEVATION_FILL))

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

# The marine names as a list, apart from the OpenStreetMap names, whose licence differs.
$(OUT)/places-gazetteers.json: $(OUT)/names.geojsons scripts/places.py
	uv run -q scripts/places.py gazetteers $< $@

# The water regions (decisions/027): one per water name the map labels, covering the water.
# Over the Salish Sea and the coasts its whales use; at about 90 m the whole range would need
# five times the memory. The two gazetteers' outlines, as their services answered on
# REGION_OUTLINES_DATE; change the date to fetch them again.
ifeq ($(REGION),coast)
  REGIONS_BBOX := -129.0,42.0,-122.0,51.5
else
  REGIONS_BBOX := $(BBOX)
endif
REGION_OUTLINES_DATE := 261028
REGION_OUTLINES_CACHE := $(CACHE)/region-outlines-$(REGION)-$(REGION_OUTLINES_DATE)
$(OUT)/region-outlines.geojsons: scripts/region_outlines.py $(REGION_SETTINGS)
	uv run -q scripts/region_outlines.py $(REGION_OUTLINES_CACHE) $@ --bbox=$(REGIONS_BBOX)
$(OUT)/regions.geojsons: $(OUT)/dem.tif $(OUT)/names.geojsons $(OUT)/region-outlines.geojsons $(OUT)/drying.geojsons \
    $(OUT)/protomaps.pmtiles $(OUT)/places-osm.json regions-known.tsv regions-overrides.json scripts/regions.py
	uv run -q scripts/regions.py $(OUT)/dem.tif $(OUT)/names.geojsons $(OUT)/region-outlines.geojsons $(OUT)/drying.geojsons \
	  $(OUT)/protomaps.pmtiles $(OUT)/places-osm.json regions-known.tsv regions-overrides.json $@ \
	  --bbox=$(REGIONS_BBOX) --report=$(OUT)/regions-report.json
# They are drawn from OpenStreetMap's land and told apart by its islands and towns, so they are
# under the ODbL, in an archive and a list of their own (Peter, 2026-10-28).
$(OUT)/regions.pmtiles: $(OUT)/regions.geojsons
	tippecanoe -q --force -o $@ -Z5 -z12 --no-feature-limit --no-tile-size-limit --detect-shared-borders \
	  --attribution="© OpenStreetMap contributors; USGS GNIS; Natural Resources Canada; NOAA" \
	  -L regions:$<
# The regions as a list a site can read, beside the place lists, to name where a sighting was.
$(OUT)/places-regions.json: $(OUT)/regions.geojsons scripts/regions_list.ts
	node scripts/regions_list.ts $< $@

# Every name is kept (-r1); each leaves the tiles below its own zoom.
$(OUT)/marine.pmtiles: $(OUT)/names.geojsons $(OUT)/boundary.geojsons
	tippecanoe -q --force -o $@ -Z5 -z12 -r1 --no-feature-limit --no-tile-size-limit \
	  --attribution="USGS GNIS; Natural Resources Canada; NOAA" \
	  -L names:$(OUT)/names.geojsons -L boundary:$(OUT)/boundary.geojsons

# Image tiles (decisions/014): the map without its labels, cut into 256-pixel tiles drawn at
# twice that, for things that stitch tiles into a picture rather than draw a map. Close-ups,
# zooms 11 to 15, only along the shore in IMAGES_CLOSE, the Salish Sea and the west coast of
# Vancouver Island's south end, where SalishSea.io's seal haul-outs are. The list is
# rewritten only when it changes, so editing the Makefile doesn't draw the tiles again.
IMAGES_CLOSE := -125.5,47.0,-122.0,50.5
IMAGES_MAXZOOM := 15
$(OUT)/images.txt: $(OUT)/dem.tif $(OUT)/protomaps.pmtiles scripts/image_tiles.py Makefile
	uv run -q scripts/image_tiles.py $< $(OUT)/protomaps.pmtiles $@.new --bbox=$(BBOX) --close=$(IMAGES_CLOSE) \
	  --maxzoom=$(IMAGES_MAXZOOM) $(if $(OVERVIEW_ARCHIVES),--overview=$(OVERVIEW_BBOX))
	@if cmp -s $@.new $@; then rm $@.new; else mv $@.new $@; fi

# The style the tiles are drawn from, rewritten only when it changes, so editing the labels
# in style/style.ts doesn't draw the tiles again.
IMAGE_STYLE := $(OUT)/images-style.json
$(IMAGE_STYLE): FORCE
	mkdir -p $(dir $@)
	node scripts/image_style.ts $(REGION) > $@.new
	@if cmp -s $@.new $@; then rm $@.new; else mv $@.new $@; fi

# The image tiles depend on what the archives hold, not on when they were written: an
# edit to the Makefile rewrites some cheap archives, the same to the byte but newer, which
# would draw every tile again (as 2026.10.8's build did). This record of their SHA-256s is
# rewritten only when one of them changes.
# The first record takes the date of tiles already drawn, which were drawn from these.
IMAGE_ARCHIVE_SUMS := $(OUT)/images-archives
SHA256 := $(shell command -v sha256sum || echo shasum -a 256)
$(IMAGE_ARCHIVE_SUMS): $(IMAGE_ARCHIVES)
	$(SHA256) $^ > $@.new
	@if cmp -s $@.new $@; then rm $@.new; \
	elif [ ! -e $@ ] && [ -e $(OUT)/images/done ]; then mv $@.new $@; touch -r $(OUT)/images/done $@; \
	else mv $@.new $@; fi

$(OUT)/images/done: $(OUT)/images.txt $(IMAGE_STYLE) $(IMAGE_ARCHIVE_SUMS) scripts/images.ts viewer/images.ts \
  viewer/images.html | assets
	node scripts/images.ts $(REGION)
	touch $@

# Landmarks (decisions/015): lighthouses, radio and television towers, and what the charts
# mark as conspicuous, from Geofabrik's OpenStreetMap extracts of the day OSM_DATE, which
# overlap at their borders. Their own archive, so a change to them doesn't draw the image
# tiles again, under the ODbL like the rest from OpenStreetMap. Geofabrik keeps each day's
# extracts for about a week, the first of each month's for about three months and the first
# of January's for good, so pin a first of the month.
OSM_DATE := 261001
OSM_FILES := $(foreach e,$(OSM_EXTRACTS),$(CACHE)/osm_$(notdir $(e))-$(OSM_DATE).osm.pbf)
define osm_download
$(CACHE)/osm_$(notdir $(1))-$(OSM_DATE).osm.pbf:
	mkdir -p $(CACHE)
	curl -sSfL --retry 5 -C - -o $$@.part https://download.geofabrik.de/$(1)-$(OSM_DATE).osm.pbf
	mv $$@.part $$@
endef
$(foreach e,$(OSM_EXTRACTS),$(eval $(call osm_download,$(e))))

# The settings record holds the region's box; the date is in the extracts' names.
$(OUT)/landmarks.geojsons: $(OSM_FILES) scripts/landmarks.py $(REGION_SETTINGS)
	mkdir -p $(OUT)
	uv run -q scripts/landmarks.py $@ $(OSM_FILES) --bbox=$(BBOX)

# Islands, towns and ferry terminals, as a list (decisions/018).
# It also says which island each of the gazetteers' places is on, from OpenStreetMap's
# outlines, so it reads the gazetteers' list.
$(OUT)/places-osm.json: $(OSM_FILES) $(OUT)/ferry_routes.geojsons $(OUT)/places-gazetteers.json scripts/places.py $(REGION_SETTINGS)
	mkdir -p $(OUT)
	uv run -q scripts/places.py osm $@ $(OSM_FILES) --bbox=$(BBOX) --routes=$(OUT)/ferry_routes.geojsons \
	  --gazetteers=$(OUT)/places-gazetteers.json

# Islets that Protomaps' tiles leave out, named from OpenStreetMap (decisions/018).
$(OUT)/islets.geojsons: $(OSM_FILES) scripts/islets.py $(REGION_SETTINGS)
	mkdir -p $(OUT)
	uv run -q scripts/islets.py $@ $(OSM_FILES) --bbox=$(BBOX)

# Protomaps' parks, national parks and nature reserves, as points with their names, kinds
# and first zooms (decisions/026). Its most detailed tiles hold every one; about 8 minutes
# over the coast.
$(OUT)/park_points.geojsons: $(OUT)/protomaps.pmtiles
	rm -f $@
	ogr2ogr -f GeoJSONSeq $@ $< pois -oo ZOOM_LEVEL=15 -t_srs EPSG:4326 \
	  -where "kind IN ('park','national_park','nature_reserve')" -select name,kind,min_zoom

# The sea as at zoom 13, sharper than sea.geojsons, for trimming nature reserves to the land.
$(OUT)/sea_z13.geojsons: $(OUT)/protomaps.pmtiles
	rm -f $@
	ogr2ogr -f GeoJSONSeq $@ $< water -oo ZOOM_LEVEL=13 -t_srs EPSG:4326 \
	  -where "kind IN ('ocean','bay','strait','sound','fjord')" -select kind

# Where each park's name goes, and the nature reserves' outlines on the land (decisions/026).
# The script writes both files, as scripts/ferries.py does.
$(OUT)/parks.geojsons: $(OUT)/park_points.geojsons $(OUT)/sea_z13.geojsons $(OSM_FILES) scripts/parks.py $(REGION_SETTINGS)
	uv run -q scripts/parks.py $(OUT)/park_points.geojsons $(OUT)/sea_z13.geojsons $@ $(OUT)/reserves.geojsons \
	  $(OSM_FILES) --bbox=$(BBOX)
$(OUT)/reserves.geojsons: $(OUT)/parks.geojsons
	@test -f $@ || { rm -f $<; $(MAKE) $<; }

# Peninsulas, named from OpenStreetMap from a zoom set by their size (decisions/023).
$(OUT)/peninsulas.geojsons: $(OSM_FILES) scripts/peninsulas.py $(REGION_SETTINGS)
	mkdir -p $(OUT)
	uv run -q scripts/peninsulas.py $@ $(OSM_FILES) --bbox=$(BBOX)

# The salmon and steelhead runs on each named river that reaches the sea (decisions/020),
# from SWIFD (WDFW and the Northwest Indian Fisheries Commission) and NuSEDS (Fisheries and
# Oceans Canada), as they were on SALMON_DATE; change the date to fetch them again. Python
# can't verify the Canadian download's certificates, so curl fetches it.
SALMON_DATE := 261020
SALMON_CACHE := $(CACHE)/salmon-$(SALMON_DATE)
NUSEDS_SITES := https://api-proxy.edh-cde.dfo-mpo.gc.ca/catalogue/records/c48669a3-045b-400d-b730-48aafe8c5ee6/attachments/Conservation%20Unit%20Census%20Sites_20250528.csv
$(SALMON_CACHE)/fetched:
	mkdir -p $(SALMON_CACHE)
	uv run -q scripts/salmon.py fetch $(SALMON_CACHE)
	curl -sSfL --retry 5 -o $(SALMON_CACHE)/nuseds-sites.csv '$(NUSEDS_SITES)'
	touch $@

# The rivers the map names when zoomed out, with their lines, read from Protomaps' tiles.
$(OUT)/rivers.geojsons: $(OUT)/protomaps.pmtiles
	rm -f $@
	ogr2ogr -f GeoJSONSeq $@ $< -oo ZOOM_LEVEL=10 -t_srs EPSG:4326 -where "kind = 'river' AND name IS NOT NULL" -select name water

# The sea, as Protomaps draws it, to tell a river's mouth on the sea from one on a lake. Reefs
# are left out: OpenStreetMap maps them in lakes too.
$(OUT)/sea.geojsons: $(OUT)/protomaps.pmtiles
	rm -f $@
	ogr2ogr -f GeoJSONSeq $@ $< -oo ZOOM_LEVEL=10 -t_srs EPSG:4326 -where "kind IN ('ocean','bay','strait','sound','fjord')" -select kind water

$(OUT)/salmon.geojsons: $(SALMON_CACHE)/fetched $(OUT)/rivers.geojsons $(OUT)/sea.geojsons $(OUT)/dem.tif scripts/salmon.py $(REGION_SETTINGS)
	uv run -q scripts/salmon.py build $(SALMON_CACHE) $(OUT)/rivers.geojsons $(OUT)/sea.geojsons $(OUT)/dem.tif $@ --bbox=$(BBOX)

# The names of islets, peninsulas and parks, and the rivers' runs, ride in the landmarks'
# archive, which is OpenStreetMap's and, like them, only labels, so the image tiles don't
# depend on any of them. Which rivers are labelled follows OpenStreetMap's names, so the
# runs are kept with its data. Its tiles start at zoom 6 for the largest peninsulas; the
# largest parks start at 7, and everything else at 9 or later, each by its own minzoom.
$(OUT)/landmarks.pmtiles: $(OUT)/landmarks.geojsons $(OUT)/islets.geojsons $(OUT)/peninsulas.geojsons $(OUT)/parks.geojsons $(OUT)/salmon.geojsons
	tippecanoe -q --force -o $@ -Z6 -z14 -r1 --no-feature-limit --no-tile-size-limit \
	  --attribution="© OpenStreetMap contributors; salmon runs: WDFW and NWIFC, Fisheries and Oceans Canada" \
	  -L landmarks:$(OUT)/landmarks.geojsons -L islets:$(OUT)/islets.geojsons \
	  -L peninsulas:$(OUT)/peninsulas.geojsons -L parks:$(OUT)/parks.geojsons -L salmon:$(OUT)/salmon.geojsons

# Shipping lanes and the other routes ships keep to (decisions/019), from NOAA's charts and
# Fisheries and Oceans Canada's routes, as their services answered on ROUTES_DATE. They are
# fetched once over the whole coast into a folder named for that date; change the date to
# fetch them again. The charts' routes rarely change: Juan de Fuca's were last amended in 2010.
ROUTES_DATE := 261019
ROUTES_CACHE := $(CACHE)/routes-$(ROUTES_DATE)
$(ROUTES_CACHE)/fetched:
	mkdir -p $(ROUTES_CACHE)
	uv run -q scripts/routes.py fetch $(ROUTES_CACHE)
	touch $@

$(OUT)/routes.geojsons: $(ROUTES_CACHE)/fetched scripts/routes.py $(REGION_SETTINGS)
	mkdir -p $(OUT)
	uv run -q scripts/routes.py build $(ROUTES_CACHE) $@ --bbox=$(BBOX)

# Each feature names its layer, `areas` or `marks`, and a mark its own first zoom.
$(OUT)/routes.pmtiles: $(OUT)/routes.geojsons
	tippecanoe -q --force -o $@ -Z6 -z12 -r1 --no-feature-limit --no-tile-size-limit \
	  --attribution="NOAA; Fisheries and Oceans Canada" $<

# The landmarks' icons, from Maki, as a sprite of their own (style/icons/).
build/sprites/landmarks.png: $(wildcard style/icons/*.svg) scripts/sprite.ts
	node scripts/sprite.ts build/sprites/landmarks
