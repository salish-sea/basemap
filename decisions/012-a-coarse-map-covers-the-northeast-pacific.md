# 012 — A coarse map covers the Northeast Pacific, for zooming out and past the edges

**Status:** accepted · **Decided:** 2026-10-14, by Peter

## Context

The coast's own layers start at zoom 5 and stop at its edges, 136–120°W and 36–54.8°N ([011](011-the-coast-covers-salishsea-ios-data.md)). A map that keeps to them has to stop people zooming out below 5 and panning past the edges. MapLibre's `maxBounds` does that by never letting the screen show anything outside the box, and the box is only 16° of longitude wide: on a screen 1440 pixels wide, it holds the map at zoom 6 or more. SalishSea.io's "SRKW Range" and "Everywhere" views, which frame 36–54°N, then show only 42–49°N, where Esri's tiles had let them frame the whole range.

## Decision

**A second, coarse map covers 180–90°W and 15–70°N,** cut from GEBCO's grid alone: the grid averaged to 0.025° (about 2.5 km), cut into depth bands with the same levels and tints as the region's and into land, and shaded for relief. It is published as two more archives, `overview` (vector tiles to zoom 5) and `overview_elevation` (elevation tiles to zoom 5). Only the coast has it; the test window has no GEBCO.

- **Below zoom 5** the map is drawn from the coarse archives: their depth bands and relief everywhere, with Protomaps' land and names on top, which at those zooms already cover a much wider area than the region, because their tiles are large.
- **From zoom 5, inside the region,** it is drawn from the region's own layers as before.
- **From zoom 5, outside the region,** the coarse depth bands and land still show, enlarged from their zoom-5 tiles, so a map panned past an edge is coarse there rather than blank. The relief stops at the region's edge.
- **The two never overlap.** The coarse bands and land are split at the region's edge ([scripts/overview_layers.sh](../scripts/overview_layers.sh)); inside it, the coarse bands are drawn only below zoom 5, so nothing is drawn twice and the region's coastline, from OpenStreetMap, is never covered by GEBCO's.

A map that keeps within 180–90°W and 15–70°N, at zoom 3 or more, never shows anything blank.

## Rejected

- **Keep maps inside the region.** Wide screens couldn't zoom out far enough to show the range the region was widened to cover.
- **Let maps go past the region with nothing there.** The flat background colour reads as missing data.
- **Build the region's own layers at every zoom over the whole Northeast Pacific.** The 30 m grids stop near the coast anyway, so most of the area would be GEBCO at a resolution nobody zooms in far enough to see, at many times the build's size and time.
