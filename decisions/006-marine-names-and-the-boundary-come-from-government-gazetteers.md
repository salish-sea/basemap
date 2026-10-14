# 006 — Marine names come from the two countries' gazetteers, and the boundary at sea from NOAA

**Status:** accepted · **Decided:** 2026-10-13, by Peter

## Context

Next to Esri's ocean basemap, which SalishSea.io uses today, ours lacked two things whale watchers read the map by.

The first is the names of the water. Protomaps labels some passages, such as Haro Strait, Boundary Pass and San Juan Channel, but few at low zooms: at MapLibre zoom 9.4 Rosario Strait had no name, where Esri shows it large. In 3,976 sighting reports, people place whales by points and capes most (22% of reports: Point Robinson, Browns Point, Bush Point, Point No Point, Lime Kiln Point), then by islands (17%), then "between X and Y" or mid-channel (13%), and by passages, inlets and bays (Saratoga Passage, Carr Inlet, Commencement Bay, Possession Sound, Penn Cove, Colvos Passage).

The second is the international boundary through the water. Protomaps draws the boundary on land only; Esri draws it dashed across the straits.

## Decision

**The names of bays, straits, channels, passages, sounds, inlets and points come from the two national gazetteers:** the USGS's [Geographic Names Information System](https://www.usgs.gov/tools/geographic-names-information-system-gnis) (GNIS) for the US side, and Natural Resources Canada's [Canadian Geographical Names Database](https://open.canada.ca/data/en/dataset/e27c6eba-3c5d-4051-9db2-082dc6411c2c) (CGNDB) for the Canadian side. They are the official names on each side of the border, and both are open: GNIS is in the public domain, and CGNDB is under the Open Government Licence – Canada, which already covers our Canadian depths.

**The boundary is NOAA's [maritime limits and boundaries](https://nauticalcharts.noaa.gov/data/us-maritime-limits-and-boundaries.html),** the line between Canada and the US that the International Boundary Commission set out, from Point Roberts through Haro Strait to the mouth of the Strait of Juan de Fuca. It is a US government work, in the public domain. It is drawn as a grey dash and dot, the usual mark of an international boundary and unlike the ferry routes' plain dashes, under all labels.

**Both go into their own archive, `marine.pmtiles`.** Neither comes from OpenStreetMap, so they stay out of the ODbL archives, and they are not depths, so they stay out of `depth.pmtiles`.

**Each name has only a point,** not the outline of the water it names, so [scripts/names.py](../scripts/names.py) uses the depth grid to judge the rest:

- A water body's label moves from its point toward the middle of the water, up to 3 km for the long, narrow kinds (straits, channels, passages) and 300 m for the rest, so that a cove's label stays in its cove.
- The label is turned to run the way the water runs furthest from its point, so that Haro Strait and Rosario Strait are written along their length, as Esri writes them.
- Each label appears from the first zoom at which it fits inside the water around it. The generic part of the name sets an earliest zoom, because a point says nothing of a feature's size: straits, sounds and inlets from zoom 6, bays and harbours from 9, channels and passages from 10, coves and the rest from 11. For Canadian names, so does the map scale CGNDB says each name is relevant at.
- A point of land is kept only if it is on the sea, and appears from zoom 10 to 13: the more open water lies off it, the earlier, so that headlands on the straits come before points inside coves.
- Where both countries record one feature, as both record Haro Strait and the Strait of Juan de Fuca, it is labelled once.

**Our names replace Protomaps' for bays, straits and fjords,** rather than filling in the ones it lacks. Drawn together, the two sets name the same strait twice in different places, and Protomaps' set covers the two countries unevenly and appears at zooms we can't choose. Protomaps' names for the ocean and seas stay, since OpenStreetMap places those from the outline of the water. Names that appear by zoom 9 (straits, sounds, inlets and the largest bays) are placed before Protomaps' island names, so that an island's name gives way to the strait beside it; later names give way to the islands.

Names are written in the existing italic blue of the sea labels, with a light halo, and are smaller and paler than the sighting dots.

## Rejected

- **BC Geographical Names**, the province's own names service. The BC Data Catalogue lists it as "Access Only", not under an open licence, and CGNDB carries the same official names for British Columbia.
- **The International Boundary Commission's own boundary file.** Its terms allow non-commercial reproduction only and reserve all other rights; NOAA's copy of the same line is in the public domain.
- **CanVec's map labels**, NRCan's cartographic name placements, which might have given label lines. Its marine names are points, like CGNDB's.

## Known problems

- Labels are placed from points, not outlines. A name whose point lies out in open water appears earlier and larger than the feature deserves: Middle Channel and Inner Passage, small passages off Lopez Island, show from zoom 10 because their points sit in the open Strait of Juan de Fuca.
- The test window ends at 124.0°W, so the Strait of Juan de Fuca is named from GNIS's point at its east end; CGNDB's point, at 124.0°W, sits on the window's edge. The whole range should name it mid-strait.
- West of the mouth of the Strait of Juan de Fuca, and in Dixon Entrance north of Haida Gwaii, NOAA's file holds only the US's own claims, which it marks as unilateral. They are left out, so the boundary at sea stops at the mouth of the strait.
- GNIS is downloaded one state at a time; the whole range will need Oregon and California as well as Washington.
- CGNDB warns that some historical names in it are offensive. Any we find on the map should be reported to the naming authority rather than edited here.
