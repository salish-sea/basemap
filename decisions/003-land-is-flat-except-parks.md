# 003 — Land is one flat colour, except parks

**Status:** accepted · **Decided:** 2026-10-13, by Peter · **Amended:** 2026-10-14, rivers

## Context

The style starts from Protomaps' light flavour, which colours land by what covers it: greens for forest, grass, scrub and parks, cream for farmland and bare ground, and other tints for hospitals, schools, airports and industry. Over the San Juan Islands this made a strong patchwork of green and yellow that tells someone looking for whales nothing and competes with the coloured sighting dots. Esri's ocean basemap, which SalishSea.io uses today, draws land in one flat colour shaped only by the relief.

## Decision

**Land is drawn in one colour, shaped by the relief,** as on Esri's ocean basemap. Protomaps' land-cover layer and its land-use fills are left out of the style.

**Parks are the exception,** in a faint green: OpenStreetMap's parks and national parks. Many are where people watch from shore, such as Lime Kiln Point State Park on San Juan Island. Piers are kept too, as part of the shoreline.

Nature reserves and protected areas are not tinted. Some of their boundaries reach out over the sea, like the reserve covering Boundary Bay down to the border, and the style can't clip a fill to the land. Mud flats are drawn from the depth grid instead ([004](004-ground-that-dries-at-low-tide-is-drawn.md)).

**Rivers and streams are drawn in a clear blue** (amended 2026-10-14). Protomaps draws them in its water colour, which this style sets to the shallowest depth tint. On flat, pale land that made rivers almost invisible, much less noticeable than an interstate, though the rivers are where salmon run. Rivers are drawn from zoom 9, where they first appear in the tiles, and streams from zoom 13, a zoom earlier than Protomaps draws them. Lakes and wide rivers, which OpenStreetMap maps as areas, are filled a step bluer than the shallowest sea when zoomed out, so the Fraser reads as plainly as its tributaries. From zoom 10 to 12 the fill fades to the sea's tint: by then a river is wide enough to read anyway, and the straight line where OpenStreetMap's area for the Fraser stops, across its mouth, would otherwise show as a hard edge, as would marina basins on the sea. The blue lines are drawn under those areas, so they show only on land, not as a thread down the middle of the Fraser.

## Known problems

- A park whose boundary in OpenStreetMap takes in the water around it would tint that water too. None shows over the Haro Strait test window now that reserves are left out.
