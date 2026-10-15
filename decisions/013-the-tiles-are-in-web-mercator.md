# 013 — The tiles are in Web Mercator

**Status:** accepted · **Decided:** 2026-10-14, by Peter

## Context

SalishSea.io's README said, from its early days, that its map was in Web Mercator (EPSG:3857) and that UTM zone 10N (EPSG:32610) "might be nicer, but would require custom raster maps". The map then ran on OpenLayers over Esri's tiles, and OpenLayers can draw in UTM, either by reprojecting image tiles in the browser, which blurs them, or from tiles made in UTM. Now there is a basemap of our own, so the question was open again: which projection should its tiles be in?

## Decision

**Every tile is in Web Mercator,** on the usual grid of zoom, column and row that web maps share: the vector tiles, the elevation tiles the relief is shaded from ([002](002-the-relief-is-shaded-by-maplibre.md)), and the image tiles to come ([SalishSea.io decision 074](https://github.com/salish-sea/salishsea-io/blob/main/docs/decisions/074-the-basemap-is-its-own-project-and-the-cards-draw-on-it.md)).

- **MapLibre reads vector tiles only on that grid,** and PMTiles, the format the archives are stored in, has no way to say which projection its tiles are in, so every program that reads it assumes Web Mercator. Any other projection would shut out MapLibre, which SalishSea.io has drawn its map with since its [decision 076](https://github.com/salish-sea/salishsea-io/blob/main/docs/decisions/076-the-map-moves-to-maplibre.md), and anyone else following the README.
- **Mercator keeps shapes true.** Its scale changes with latitude, but across the Salish Sea, 47–50°N, by only about ±3%, so at the zooms where sightings are read it looks almost the same as UTM. Where it does stretch is zoomed out: distances are drawn 1.24 times as long at 36°N as at the equator, 1.73 times at 54.8°N and 2.9 times at 70°N, so Alaska looks large beside California. A map that minds this can use MapLibre's globe projection, which redraws Web Mercator tiles on a sphere; that is a choice for the map, not for the tiles. In a trial on version 2026.10.5, the globe drew every layer, relief included, with no errors, and at zoom 9 over the San Juans it looked the same as Mercator. At zoom 3 it showed the whole of the coarse map's coverage as a curved patch with plain background around it, because on a globe `maxBounds` doesn't keep the view inside the box the way it does in Mercator; a map that uses the globe needs a higher minimum zoom, or wider coverage.

**Inside the build, the depth grids are blended and contoured in longitude and latitude** (EPSG:4326, `WARP_FLAGS` in the [Makefile](../Makefile)), which makes a grid cell at 48°N about two-thirds as wide as it is tall, so contours are smoothed a little more north–south than east–west. No contour has yet looked wrong for it. If one does, the fix is to do that work in Web Mercator, whose cells are square on the ground and which the tiles end up in anyway, rather than in UTM. Web Mercator's metres are ground metres only at the equator: one covers 0.81 m on the ground at 36°N, 0.67 m at 48°N and 0.58 m at 54.8°N, so a setting written in metres, such as a smoothing tolerance, has to be picked for the latitude where it matters most.

## Rejected

- **UTM zone 10N.** Its metres are true to within 0.1% near its central meridian, 123°W, and north is straight up there. But it is accurate only between about 126°W and 120°W, while the coast runs from 136°W to 120°W ([011](011-the-coast-covers-salishsea-ios-data.md)) and the coarse map from 180°W to 90°W ([012](012-a-coarse-map-covers-the-northeast-pacific.md)): Haida Gwaii and Southeast Alaska would be visibly bent, and the Aleutians badly. Covering the coast would take three zones and seams between them. And MapLibre could not draw it at all.
