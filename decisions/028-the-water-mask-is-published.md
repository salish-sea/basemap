# 028 — The water mask is published

**Status:** accepted · **Decided:** 2026-11-04, by Peter, in conversation with the assistant

## Context

SalishSea.io wants to measure the distance between two sighting reports by sea rather than in a straight line, so that a track never joins reports across an island, and a leg with land between its ends can be drawn along the water (SalishSea.io's `salish-3zok.32`, for its epic `salish-20u7`). That needs to know, for any point, whether it is water, and which water connects to which.

[scripts/regions.py](../scripts/regions.py) already builds that: its first step ([027](027-every-water-name-has-a-region-and-the-regions-cover-the-water.md)) makes a grid of about 90 m from the depth grid below zero and the ground that dries at low tide, less the land of NOAA's charts and of British Columbia, keeping only water that reaches the open sea without passing a lock. Then it grows the regions through that grid. The grid itself was thrown away.

## Decision

**Each version publishes the grid of step 1 as it is before any region is grown through it:** `water/water-mask-<hash>.png`, and beside it `water/water-mask-<hash>.json`, which says where the grid lies. Both are named for their contents, as the place lists are ([018](018-the-names-the-map-labels-are-published-as-lists.md)), so a version that doesn't change the grid shares the earlier version's files. They sit under `water/` and not `places/`, because the lists there are all names and a site that reads `salishsea:places` expects each URL to be one.

- **The PNG is 1-bit greyscale:** white (1) is water and black (0) is land. Its rows run from north to south and its columns from west to east, exactly the grid `regions.py` works on, over 129°W to 122°W and 42°N to 51.5°N: 5,600 by 11,405 cells, 177 KB. A browser decodes it natively, and Node can with a small library. The writer is a few lines of Python with `zlib` ([png_1bit](../scripts/regions.py)), checked by reading its output back with GDAL and by hand ([scripts/check_mask.py](../scripts/check_mask.py)).
- **The JSON gives the box** `[W, S, E, N]` in degrees, the `width` and `height` in cells, the `cell` size in degrees (longitude, then latitude), the value that means `water`, an `about` paragraph, and the sources, licence and attribution as `places-regions.json` states them. Nothing in the mask comes from OpenStreetMap, so it keeps the governments' terms.
- **The style names them in its metadata** under `salishsea:water` as `{"mask": <PNG URL>, "grid": <JSON URL>}`, and the version's index page lists them.
- **One run of `regions.py` writes them with the regions** (`--mask`), so the mask is always the grid the regions were grown through. `--mask-only` stops after writing it.

## Rejected

- **The regions as the mask.** Each region reaches 300 m onto the shore (step 5 of 027, the skirt), so a point on a beach is inside one. Water and land cannot be told apart by them.
- **A vector polygon of the sea.** It has about 210,000 vertices, and whoever uses it has to rasterise it to ask whether a cell is water, so the grid is the more direct form.
- **OpenStreetMap's coastline for the shore.** It is finer at narrow passes, and it would now be allowed: nothing from the tracks reaches SalishSea.io's Darwin Core archive, so the ODbL would not follow a mask into it as it would have followed a region's name (027). It is left for a later version, so that the first mask shares the regions' grid exactly and the two cannot disagree.

## Known problems

- A channel narrower than a cell is land. At about 90 m, passes a ferry uses are open (see below) but they are one or two cells wide, so a route through one has no room to bend; a narrower one would be shut.
- A bay whose mouth is narrower than a cell is cut off from the sea, and is left out of the mask as a lake would be.
- The grid's zero is not the same height in the two countries' grids ([001](001-canadas-depth-grid-is-used-wherever-it-has-data.md)): NOAA's is near mean sea level and Canada's is a low-water chart datum. So the shore is drawn at different tide heights on either side of the border, and flats that dry count as water only where the drying outlines say so.
- Fresh water above sea level, and water behind a lock, is land (027).

## What the build was checked against

Seven passes were checked over the whole-coast build on disk at the time with [scripts/check_mask.py](../scripts/check_mask.py), which looks for the narrowest part within about 1 km of the given point and whether closing it would cut the water in two. Every one was open water in the mask. Dodd Narrows joins only diagonally, cell to cell at the corners, and Deception Pass and Active Pass are one to two cells across; Sansum Narrows is three to four, Porlier Pass seven to eight and the Tacoma Narrows eleven to twelve. Pole Pass, at the position it was asked for, is in a channel 1.8 km wide: the gazetteer puts the pass 2 km to the south-south-west, and there the mask shows it three to four cells across.
