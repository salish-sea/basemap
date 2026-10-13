# Salish Sea basemap

A basemap of the Northeast Pacific coast, from Monterey Bay to Haida Gwaii, built from open data for [SalishSea.io](https://salishsea.io) and [Orcasound](https://live.orcasound.net). It keeps showing depth and shoreline at the zooms where Esri's ocean tiles go blank, and it is drawn so that the coloured dots of whale sightings stay the most visible thing on the map.

**Status: first build, over a test window around Haro Strait (124.0–122.2°W, 48.0–49.2°N).** Nothing serves it yet. Two ways of drawing the relief are being compared: shading baked into image tiles, and shading computed by MapLibre from elevation tiles.

## What it publishes

From one style, two forms of the same map:

- **Vector tiles and a MapLibre style**, for interactive maps. Vectors stay sharp at any zoom and can be restyled without a rebuild.
- **Image tiles rendered from that style** (256-pixel), for anything that stitches images together rather than drawing a map, such as SalishSea.io's preview cards and the small maps on its profile pages.

They will be served from `tiles.salishsea.io`, each build under its own versioned path, so that a rebuild never changes what a published page shows.

## What it is built from

| Layer | Source | Terms |
|---|---|---|
| Land, roads, places, water outlines | [Protomaps](https://protomaps.com) daily build of OpenStreetMap | ODbL |
| Depths south of 49°N | NOAA [Coastal Relief Model](https://www.ncei.noaa.gov/products/coastal-relief-model), 1 arc-second (about 30 m) | Public domain |
| Depths north of 49°N | Natural Resources Canada's [West Coast topo-bathymetric DEM](https://open.canada.ca/data/dataset/e6e11b99-f0cc-44f7-f5eb-3b995fb1637e), resampled from 10 m to 30 m | Open Government Licence – Canada |

Why one 30 m grid, and why not the Canadian Hydrographic Service's own depths, is in SalishSea.io's decision [073](https://github.com/salish-sea/salishsea-io/blob/main/docs/decisions/073-the-basemap-depths-are-30-m-lightly-shaded.md). Why the basemap is its own project is in [074](https://github.com/salish-sea/salishsea-io/blob/main/docs/decisions/074-the-basemap-is-its-own-project-and-the-cards-draw-on-it.md). Decisions made from here on are recorded in [decisions/](decisions/).

Anything derived from OpenStreetMap is kept in its own archive, so that the ODbL's share-alike terms don't reach the public-domain and Canadian data. The map is not for navigation.

## How depth is drawn

Depth is drawn in two ways, both cut from the same elevation grid:

- **Depth bands and isobaths** are vector polygons and lines, darker where deeper. Isobaths carry their depth as a label.
- **Relief**, the light and shadow of the seafloor and land, sits above the land and the bands but under roads and labels, and fades out before it would blur. It is either baked into translucent image tiles (`shade.pmtiles`), or computed by MapLibre's `hillshade` layer from elevation tiles in Mapzen's Terrarium encoding (`elevation.pmtiles`), so it can be restyled without a rebuild. [scripts/raster_tiles.py](scripts/raster_tiles.py) writes both.

## Building

The style is [style/style.ts](style/style.ts), built on Protomaps' light flavour. The build needs GDAL, tippecanoe, the `pmtiles` command, `uv` and Node (version in [.nvmrc](.nvmrc)). Source grids are downloaded once into `cache/`, which is not committed.

```sh
pnpm install
make window      # every archive for the test window, in build/window/
make serve       # a page that compares versions of our map, and Esri's, side by side
```

## Licence

Code is MIT; documentation and the style are CC BY 4.0. Built tiles carry their sources' terms (above). See [LICENSE](LICENSE).
