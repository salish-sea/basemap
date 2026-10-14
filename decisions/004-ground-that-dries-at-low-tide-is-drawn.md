# 004 — Ground that dries at low tide is drawn

**Status:** accepted · **Decided:** 2026-10-13, by Peter

## Context

OpenStreetMap draws the coastline at high water, so everything below it, including mud flats that are bare at low tide, is sea on our map. Boundary Bay is mostly such flats, but the map showed it either as open water or, for a while, under the green of a nature reserve whose boundary runs out over the bay to the border ([003](003-land-is-flat-except-parks.md)).

Canada's depth grid is measured from chart datum, about the lowest tide ([001](001-canadas-depth-grid-comes-first.md)). So ground that dries at low tide has a height above 0 m in it: Boundary Bay's flats are 1.5–2.2 m.

## Decision

**Ground between 0 and 5 m in the depth grid is drawn in a khaki tint, under the land,** the way nautical charts colour drying areas. Drawn under OpenStreetMap's land, it shows only below the high-water coastline, so 5 m only needs to be above the highest tides; the coastline decides where the drying ground ends.

## Known problems

- South of about 47.4°N, the depth grid is NOAA's, measured from about mean sea level. There only the upper half of the drying ground is above 0 m, so less of it shows.
