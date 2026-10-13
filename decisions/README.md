# Decisions

Numbered records of decisions about the basemap: what it is built from, how it is drawn, and how it is served. Each record says what was decided, why, and what was rejected. Superseded records are marked, not deleted.

The decisions that started this project were made in SalishSea.io and stay there:

- [068](https://github.com/salish-sea/salishsea-io/blob/main/docs/decisions/068-the-map-stays-on-openlayers.md): SalishSea.io builds its own basemap. (Its choice of OpenLayers is superseded by [076](https://github.com/salish-sea/salishsea-io/blob/main/docs/decisions/076-the-map-moves-to-maplibre.md): the map is drawn by MapLibre GL.)
- [073](https://github.com/salish-sea/salishsea-io/blob/main/docs/decisions/073-the-basemap-depths-are-30-m-lightly-shaded.md): one 30 m depth grid for the whole range, Canada's wherever it has data and NOAA's elsewhere, shaded lightly by MapLibre (amended 2026-10-13).
- [074](https://github.com/salish-sea/salishsea-io/blob/main/docs/decisions/074-the-basemap-is-its-own-project-and-the-cards-draw-on-it.md): the basemap is this repository, served from tiles.salishsea.io as vector and image tiles.
