# 003 — Land is one flat colour, except parks

**Status:** accepted · **Decided:** 2026-10-13, by Peter

## Context

The style starts from Protomaps' light flavour, which colours land by what covers it: greens for forest, grass, scrub and parks, cream for farmland and bare ground, and other tints for hospitals, schools, airports and industry. Over the San Juan Islands this made a strong patchwork of green and yellow that tells someone looking for whales nothing and competes with the coloured sighting dots. Esri's ocean basemap, which SalishSea.io uses today, draws land in one flat colour shaped only by the relief.

## Decision

**Land is drawn in one colour, shaped by the relief,** as on Esri's ocean basemap. Protomaps' land-cover layer and its land-use fills are left out of the style.

**Parks are the exception,** in a faint green: OpenStreetMap's parks and national parks. Many are where people watch from shore, such as Lime Kiln Point State Park on San Juan Island. Piers are kept too, as part of the shoreline.

Nature reserves and protected areas are not tinted. Some of their boundaries reach out over the sea, like the reserve covering Boundary Bay down to the border, and the style can't clip a fill to the land. Mud flats are drawn from the depth grid instead ([004](004-ground-that-dries-at-low-tide-is-drawn.md)).

## Known problems

- A park whose boundary in OpenStreetMap takes in the water around it would tint that water too. None shows over the Haro Strait test window now that reserves are left out.
