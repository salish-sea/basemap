# Decisions

Numbered records of decisions about the basemap: what it is built from, how it is drawn, and how it is served. Each record says what was decided, why, and what was rejected. Superseded records are marked, not deleted.

The decisions that started this project were made in SalishSea.io and stay there:

- [068](https://github.com/salish-sea/salishsea-io/blob/main/docs/decisions/068-the-map-stays-on-openlayers.md): SalishSea.io builds its own basemap. (Its choice of OpenLayers is superseded by [076](https://github.com/salish-sea/salishsea-io/blob/main/docs/decisions/076-the-map-moves-to-maplibre.md): the map is drawn by MapLibre GL.)
- [073](https://github.com/salish-sea/salishsea-io/blob/main/docs/decisions/073-the-basemap-depths-are-30-m-lightly-shaded.md): one 30 m depth grid for the whole range, shaded lightly. (Amended by 001 and 002 below.)
- [074](https://github.com/salish-sea/salishsea-io/blob/main/docs/decisions/074-the-basemap-is-its-own-project-and-the-cards-draw-on-it.md): the basemap is this repository, served from tiles.salishsea.io as vector and image tiles.

Recorded here:

- [001](001-canadas-depth-grid-comes-first.md): Canada's depth grid is used wherever it has data, NOAA's elsewhere, each kept in its own vertical datum.
- [002](002-the-relief-is-shaded-by-maplibre.md): the relief is shaded by MapLibre from elevation tiles, not baked into image tiles.
- [003](003-land-is-flat-except-parks.md): land is one flat colour, shaped by the relief, except for parks in a faint green.
- [004](004-ground-that-dries-at-low-tide-is-drawn.md): ground that dries at low tide is drawn from the depth grid, in khaki.
- [005](005-ferry-routes-are-drawn-from-zoom-9.md): ferry routes are drawn from zoom 9, one line per channel up to zoom 12, and named from zoom 11.
- [006](006-marine-names-and-the-boundary-come-from-government-gazetteers.md): marine names come from GNIS and Canada's names database, placed and timed against the depth grid, and replace Protomaps' names for bays and straits; the boundary at sea is NOAA's.
- [007](007-published-builds-are-dated-and-never-change.md): each build is published once, under a dated path on tiles.salishsea.io, and never changed.
