# 011 — The coast covers SalishSea.io's data

**Status:** accepted · **Decided:** 2026-10-14, by Peter

## Context

The coast region was first drawn as 134.0–121.7°W, 36.4–54.8°N: Monterey Bay to Haida Gwaii, as far offshore as the shelf and as far inland as the Cascades. SalishSea.io takes killer whale sightings from Maplify across the Southern Residents' whole range, which its ingest bounds as 136–120°W, 36–54°N (`acartiaExtent` in [SalishSea.io's src/extents.ts](https://github.com/salish-sea/salishsea-io/blob/main/src/extents.ts)). That reaches two degrees further offshore, a degree and a half further inland, up the Columbia, and a little further south.

Nothing is drawn outside the region, so a map that switched to the basemap had two choices: stop people panning past its edges, which would hide sightings out there, or let them pan onto a blank map.

## Decision

**The coast region covers SalishSea.io's data: 136–120°W, 36–54.8°N.** The north edge stays at 54.8°N, past the data's 54°N, so that the region still takes in Dixon Entrance. A map using the basemap can then keep to the region, with MapLibre's `maxBounds`, and hide nothing.

The wider area adds no new sources. GEBCO's grid already fills everything the 30 m grids don't, offshore and inland (decision [009](009-gebco-fills-the-deep-ocean.md)); inland past the 30 m grids, the land's relief comes from GEBCO's 450 m cells and so is coarser.

## Rejected

- **Keep the region and stop maps at its edges.** Cheaper, but it hides sightings far offshore and up the Columbia, which the site exists to show.
- **Keep the region and let maps pan past it.** The map would show the plain background colour there, which reads as missing data.
