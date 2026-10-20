# 019 — Shipping lanes are drawn from the two countries' charts, on the map but not in the image tiles

**Status:** accepted · **Decided:** 2026-10-19, by Peter · **Follows:** SalishSea.io's `salish-3zok.11`, split from the research on whale protection zones in `salish-3zok.9`

## Context

Sighting reports place whales by the shipping lanes: "east of the northbound lane", "in the separation zone". The map showed none of them. The lanes, and the separation zones between opposing lanes, are traffic separation schemes adopted by the IMO, charted by both countries.

There are two open sources. NOAA's [ENC Direct](https://encdirect.noaa.gov/) serves the US electronic charts' routeing areas, in the public domain and updated weekly. Fisheries and Oceans Canada's [Vessel Traffic Routes](https://open.canada.ca/data/en/dataset/6ab2803a-aace-4e60-83ed-44a7e0ccd1d8) serves Canada's, under the Open Government Licence – Canada. OpenSeaMap's tags in OpenStreetMap hold about 180 such features around the Salish Sea, unsourced and under the ODbL, and are not used.

## Decision

**The map draws the charts' routeing areas from zoom 8** ([scripts/routes.py](../scripts/routes.py), [style/style.ts](../style/style.ts), `routeLayers`):

- **separation zones**, the bands between opposing lanes, as a faint tint;
- **lanes** of traffic separation schemes, recommended lanes and **two-way routes**, outlined;
- **precautionary areas**, where lanes meet and ships must take care, dashed;
- from zoom 9, an **arrow** every 6 km along each lane, pointing its way, or both ways along a two-way route;
- from zoom 11, each lane's **name** by its direction, "Northbound lane" or "Two-way route", written along it, as reports name them.

All of it is one colour, `#c2185b`, a deep raspberry near the charts' magenta. Chart magenta itself is too close to two of SalishSea.io's sighting colours, the otter's pink `#CC79A7` and the toothed whale's violet `#5B2C8D`. This colour keeps a perceptual distance (CIE ΔE) of at least 37 from every one of them, against 27 to 31 for magentas nearer the charts'. The lines are thin and the tint faint, and the arrows and names give way to depth labels and water names, so that sightings stay the most visible thing on the map.

**NOAA's areas are used wherever NOAA charts; Canada's fill the gaps** (Peter). NOAA's coastal charts cover US waters and, from cells compiled from Canada's charts, Haro Strait and Boundary Pass too. Canada's areas are added only where NOAA has nothing, such as the schemes off the Fraser River and Vancouver, cut away where they overlap NOAA's, and a sliver or scrap that is left is dropped. Over the coast that is 132 areas from NOAA and 7 from Canada. Pieces of one area that the charts cut at their cells' edges are joined, so no line crosses a lane where a cell ends.

**The lanes are on the map people pan and zoom, and not in the image tiles** (Peter). Preview cards, profile maps and small maps are about the sightings, and magenta across the Strait of Juan de Fuca on most cards would compete with them. The image tiles' style leaves out the lanes' source and layers, as it leaves out the landmarks ([decision 014](014-image-tiles-are-drawn-from-the-style-along-the-shore.md)), so adding them draws no tile again.

**The lanes are an archive of their own, `routes`,** fetched once over the whole coast into a folder named for the date they were fetched (the Makefile's `ROUTES_DATE`), and fetched again only when that date changes. The charts' schemes change rarely: Juan de Fuca's was last amended in 2010.

## Rejected

- **Each side of the border from its own country's source,** as `salish-3zok.11` first proposed. The boundary runs down the middle of Haro Strait and Boundary Pass, so the route there would have been two sources' drawings joined along a seam down the channel.
- **The lanes in the image tiles too.** Every card would carry them, and every image tile would be drawn again.
- **OpenSeaMap's tags in OpenStreetMap.** Unsourced, and under the ODbL, which would have kept the lanes apart from the public-domain and Canadian data they belong with.
- **Chart magenta.** Too close to the otter's and toothed whale's colours on SalishSea.io's map.
- **Hatching the separation zones.** It needs a pattern image in the sprite; the charts themselves tint them.

## Known problems

- NOAA's and Canada's services answer queries for the current charts only. A build on a machine without the fetched folder fetches the routes as they are that day, under the old date's name.
- Recommended tracks, leading lines into harbours and fairways in Puget Sound are not drawn.
- The arrows and names are text, the font's own arrows, turned on the map; they are thin at the closest zooms.
- Whale protection zones, which change by season and by year, are not drawn; how the map should show a zone in force on a sighting's date is open (`salish-3zok.9`).
