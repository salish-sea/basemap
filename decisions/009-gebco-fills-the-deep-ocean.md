# 009 — GEBCO fills the deep ocean, and every grid is blended in at its edges

**Status:** accepted · **Decided:** 2026-10-13 · **Amends:** SalishSea.io's [073](https://github.com/salish-sea/salishsea-io/blob/main/docs/decisions/073-the-basemap-depths-are-30-m-lightly-shaded.md), whose grids stop at the edge of the continental margin

## Context

073 chose 30 m grids that cover the coast: NOAA's Coastal Relief Model volumes and Canada's West Coast DEM. Over the whole range, Monterey Bay to Haida Gwaii, they leave more than half the area with no depth at all: NOAA's volumes 7 and 8 stop at 127°W, its Southern California grid at 123°W, and Canada's grid only reaches far offshore in the north. Drawn as it was, the relief stepped from about −3000 m to 0 m along those edges, over about 1,300 km.

## Decision

**GEBCO's global grid lies under everything,** at 15 arc-seconds (about 450 m), interpolated to the 1-arc-second lattice. It is the depth wherever no finer grid reaches. GEBCO is in the public domain and asks to be cited as: GEBCO Bathymetric Compilation Group 2026 (2026), The GEBCO_2026 Grid, doi:10.5285/4f68d5c7-45eb-f999-e063-7086abc036fa.

**Every layer is laid over the ones before it and blended in at its edges** ([scripts/mosaic.py](../scripts/mosaic.py)): GEBCO, then NOAA's grids, then Canada's. Within 4 km of the edge of a layer's data, it is mixed with what lies beneath, so its edge leaves no step: not at 127°W, and not along the straight edge of Canada's grid at 48.06°N ([001](001-canadas-depth-grid-comes-first.md)).

**NOAA's grids are one layer.** Its Southern California grid and volumes 7 and 8 meet edge to edge, at 37°N and 44°N. Blended separately, each would fade to GEBCO at those edges, leaving an 8 km strip of GEBCO's coarse data between them.

## Known problems

- Monterey Bay comes only from NOAA's Southern California grid, which is in whole metres and doesn't declare its vertical datum, so its shallow bands and isobaths are coarser than elsewhere.
- Where that grid meets volume 7, at 37°N just north of Santa Cruz, there is no blend, so any difference between their datums shows as a step. The alternative was a strip of GEBCO.
- In the deep ocean the relief is as smooth as GEBCO's 450 m cells; that is where sightings are fewest.
