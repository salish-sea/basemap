# 003 — Land is one flat colour, except parks

**Status:** accepted · **Decided:** 2026-10-13, by Peter

## Context

The style starts from Protomaps' light flavour, which colours land by what covers it: greens for forest, grass, scrub and parks, cream for farmland and bare ground, and other tints for hospitals, schools, airports and industry. Over the San Juan Islands this made a strong patchwork of green and yellow that tells someone looking for whales nothing and competes with the coloured sighting dots. Esri's ocean basemap, which SalishSea.io uses today, draws land in one flat colour shaped only by the relief.

## Decision

**Land is drawn in one colour, shaped by the relief,** as on Esri's ocean basemap. Protomaps' land-cover layer and its land-use fills are left out of the style.

**Parks are the exception,** in a faint green: parks, national parks, nature reserves and protected areas. Many are where people watch from shore, such as Lime Kiln Point State Park on San Juan Island. Piers are kept too, as part of the shoreline.

## Known problems

- Where a marine park's boundary in OpenStreetMap takes in the water around an island, the faint green covers that water too. One shows west of Orcas Island at about z10.
