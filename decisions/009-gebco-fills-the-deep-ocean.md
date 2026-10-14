# 009 — GEBCO fills the deep ocean, and every grid is blended in at its edges

**Status:** accepted · **Decided:** 2026-10-13 · **Amends:** SalishSea.io's [073](https://github.com/salish-sea/salishsea-io/blob/main/docs/decisions/073-the-basemap-depths-are-30-m-lightly-shaded.md), whose grids stop at the edge of the continental margin

## Context

073 chose 30 m grids that cover the coast: NOAA's Coastal Relief Model volumes and Canada's West Coast DEM. Over the whole range, Monterey Bay to Haida Gwaii, they leave more than half the area with no depth at all: NOAA's volumes 7 and 8 stop at 127°W, its Southern California grid at 123°W, and Canada's grid only reaches far offshore in the north. Drawn as it was, the relief stepped from about −3000 m to 0 m along those edges, over about 1,300 km.

## Decision

**GEBCO's global grid lies under everything,** at 15 arc-seconds (about 450 m), interpolated to the 1-arc-second lattice. It is the depth wherever no finer grid reaches. GEBCO is in the public domain and asks to be cited as: GEBCO Bathymetric Compilation Group 2026 (2026), The GEBCO_2026 Grid, doi:10.5285/4f68d5c7-45eb-f999-e063-7086abc036fa.

**Every grid is laid over the ones before it and blended in at its edges** ([scripts/mosaic.py](../scripts/mosaic.py)): GEBCO, then NOAA's Southern California grid, volumes 7 and 8, then Canada's. Within 4 km of the edge of a grid's data, it is mixed with what lies beneath, so no edge leaves a step: not 127°W, not the join at 37°N, and not the straight edge of Canada's grid at 48.06°N ([001](001-canadas-depth-grid-comes-first.md)).

## Known problems

- Monterey Bay comes only from NOAA's Southern California grid, which is in whole metres and doesn't declare its vertical datum, so its shallow bands and isobaths are coarser than elsewhere.
- In the deep ocean the relief is as smooth as GEBCO's 450 m cells; that is where sightings are fewest.
