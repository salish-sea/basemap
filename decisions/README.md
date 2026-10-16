# Decisions

Numbered records of decisions about the basemap: what it is built from, how it is drawn, and how it is served. Each record says what was decided, why, and what was rejected. Superseded records are marked, not deleted.

The decisions that started this project were made in SalishSea.io and stay there:

- [068](https://github.com/salish-sea/salishsea-io/blob/main/docs/decisions/068-the-map-stays-on-openlayers.md): SalishSea.io builds its own basemap. (Its choice of OpenLayers is superseded by [076](https://github.com/salish-sea/salishsea-io/blob/main/docs/decisions/076-the-map-moves-to-maplibre.md): the map is drawn by MapLibre GL.)
- [073](https://github.com/salish-sea/salishsea-io/blob/main/docs/decisions/073-the-basemap-depths-are-30-m-lightly-shaded.md): one 30 m depth grid for the whole range, shaded lightly. (Amended by 001 and 002 below.)
- [074](https://github.com/salish-sea/salishsea-io/blob/main/docs/decisions/074-the-basemap-is-its-own-project-and-the-cards-draw-on-it.md): the basemap is this repository, served from tiles.salishsea.io as vector and image tiles.

Recorded here:

- [001](001-canadas-depth-grid-comes-first.md): Canada's depth grid is used wherever it has data, NOAA's elsewhere, each kept in its own vertical datum.
- [002](002-the-relief-is-shaded-by-maplibre.md): the relief is shaded by MapLibre from elevation tiles, not baked into image tiles.
- [003](003-land-is-flat-except-parks.md): land is one flat colour, shaped by the relief, except for parks in a faint green; rivers and streams are a clear blue.
- [004](004-ground-that-dries-at-low-tide-is-drawn.md): ground that dries at low tide is drawn from the depth grid, in khaki.
- [005](005-ferry-routes-are-drawn-from-zoom-9.md): ferry routes are drawn from zoom 9, one line per channel up to zoom 12, and named from zoom 11.
- [006](006-marine-names-and-the-boundary-come-from-government-gazetteers.md): marine names come from GNIS and Canada's names database, placed and timed against the depth grid, and replace Protomaps' names for bays and straits; the boundary at sea is NOAA's.
- [007](007-published-builds-are-dated-and-never-change.md): each build is published once, under a CalVer path on tiles.salishsea.io such as `2026.10.1`, tagged in git, and never changed; versions share archives, each stored once under a name made from its contents.
- [008](008-full-builds-run-on-a-fly-machine.md): full builds run on a temporary Fly machine with a volume for the source grids, and publish from there.
- [009](009-gebco-fills-the-deep-ocean.md): GEBCO's global grid fills the deep ocean, and every grid is blended in at its edges.
- [010](010-fonts-and-icons-are-served-with-the-tiles.md): the labels' fonts and the icons are copied from Protomaps' assets at one commit and served from tiles.salishsea.io, under a path that never changes.
- [011](011-the-coast-covers-salishsea-ios-data.md): the coast region covers SalishSea.io's killer whale data, 136–120°W, 36–54.8°N.
- [012](012-a-coarse-map-covers-the-northeast-pacific.md): a coarse map from GEBCO covers 180–90°W, 15–70°N, so maps can zoom out to 3 and pan past the region without anything blank.
- [013](013-the-tiles-are-in-web-mercator.md): every tile is in Web Mercator, because MapLibre draws no other grid and PMTiles can't name another; UTM zone 10N was rejected, as it fits only 126–120°W.
- [014](014-image-tiles-are-drawn-from-the-style-along-the-shore.md): image tiles, for pictures stitched from tiles, are drawn from the style without its labels, by MapLibre GL in headless Chromium; zooms 11 to 15 only along the Salish Sea's shore.
- [015](015-landmarks-are-what-the-charts-mark-and-tall-towers.md): landmarks are named lighthouses and major lights, what the charts mark as conspicuous, and radio and television towers that are charted or 100 m tall, from OpenStreetMap; points within 500 m are one landmark.
- [016](016-points-of-interest-are-where-people-watch-from.md): of Protomaps' points of interest, only beaches, parks, forests, peaks, marinas, ferry terminals, aerodromes, museums, zoos, and at the closest zooms benches, toilets and drinking water; shops, restaurants and other businesses are left out.
- [017](017-depth-labels-are-level.md): depth labels are drawn level and upright on their lines, not turned to follow them, because a 1 turned along a climbing line reads as a 7.
