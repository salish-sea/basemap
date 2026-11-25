# Changelog

What changed in each version of the basemap, newest first. Each version's index page shows its map, every name it labels and every file it is made of.

## Unreleased

- Each version's index page shows its map, and a table of every name the map labels from our own archives and every place in the search lists, to filter by name and layer; choosing one moves the map to it. The same rows are in `names.tsv` beside the page, each with a link that opens the map there.
- The image tiles stop at zoom 14, which cuts the coast's set from 63,935 tiles to 28,066 ([decision 014](decisions/014-image-tiles-are-drawn-from-the-style-along-the-shore.md)). They cover the same ground at zooms 11 to 14 as before. A picture framed closer than zoom 14 shows zoom 14's tiles enlarged, as SalishSea.io's site maps and cards do since salish-sea/salishsea-io#911; a site that asks for zoom-15 tiles gets none.
- The water mask no longer has gaps in spits and jetties narrower than one of its cells, about 90 m. A route by sea used to pass through such land: a track at Port Angeles ran straight across Ediz Hook, and now goes around its tip ([decision 028](decisions/028-the-water-mask-is-published.md)).
- The image tiles and the comparison page are drawn with MapLibre 6.19.

## 2026.11.3 — 2026-11-15

[Index page](https://tiles.salishsea.io/2026.11.3/index.html) · [Changes](https://github.com/salish-sea/basemap/compare/2026.11.2...2026.11.3)

- A third place list, `places-parks.json`, holds the Salish Sea's parks, nature reserves and national parks whose land comes within 100 m of the sea: 1,465 parks, including small ones the map names only at close zooms, such as Stamm Overlook Park. The style names it under `salishsea:places` as `parks`. A site's search should not load it; the two lists the search uses are unchanged ([decision 018](decisions/018-the-names-the-map-labels-are-published-as-lists.md)).
- The map uses OpenStreetMap data from Protomaps' build of 2026-11-15.

## 2026.11.2 — 2026-11-05

[Index page](https://tiles.salishsea.io/2026.11.2/index.html) · [Changes](https://github.com/salish-sea/basemap/compare/2026.11.1...2026.11.2)

- Mountains are shaded more lightly. The Olympics, the Cascades and the Coast Mountains had been the darkest part of the map at zooms 9 and 10, which made rivers hard to follow through them. Low islands such as the San Juans keep most of their shape, and the seafloor looks as before ([decision 002](decisions/002-the-relief-is-shaded-by-maplibre.md)).
- Changing how strongly the land is shaded now means rebuilding the elevation archives, not editing the style.

## 2026.11.1 — 2026-11-05

[Index page](https://tiles.salishsea.io/2026.11.1/index.html) · [Changes](https://github.com/salish-sea/basemap/compare/2026.10.22...2026.11.1)

- The water mask is published: a 1-bit PNG of the water (5,600 by 11,405 cells over 129 to 122°W and 42 to 51.5°N) and a JSON file that gives its box, cell size, sources and licence. It lets a site measure the distance between two points by sea rather than in a straight line. The style names both under `salishsea:water`, and the index page lists them. Search through the mask must allow diagonal moves, or Dodd Narrows is shut ([decision 028](decisions/028-the-water-mask-is-published.md)).
- The map uses OpenStreetMap data from Protomaps' build of 2026-11-05.
- The comparison page now shows the map beside the same map without its relief, instead of beside Esri's ocean basemap.

## 2026.10.22 — 2026-10-29

[Index page](https://tiles.salishsea.io/2026.10.22/index.html) · [Changes](https://github.com/salish-sea/basemap/compare/2026.10.21...2026.10.22)

- This version restores the relief shading that 2026.10.21 lacked, and is otherwise the same map. The build now refuses to publish an archive that is empty or cut short.

## 2026.10.21 — 2026-10-29

[Index page](https://tiles.salishsea.io/2026.10.21/index.html) · [Changes](https://github.com/salish-sea/basemap/compare/2026.10.20...2026.10.21)

- This is the first published version with water regions: one region for each water name the map labels, together covering the water. They are in an archive of their own, `regions.pmtiles`, which the image tiles leave out and the style draws only when a page turns two hidden layers on, and in a list, `places-regions.json`, beside the place lists. The regions are made from government data only, so Lake Washington and Salmon Bay, which reach the sea only through a lock, are left out ([decision 027](decisions/027-every-water-name-has-a-region-and-the-regions-cover-the-water.md)).
- This version was published with an empty elevation archive, so it has no relief shading. Use 2026.10.22 or later.
- The map uses OpenStreetMap data from Protomaps' build of 2026-10-29.

## 2026.10.20 — 2026-10-29

[Changes](https://github.com/salish-sea/basemap/compare/2026.10.19...2026.10.20)

- This version was never published, because its build failed while writing the index page. Its changes, the water regions, are in 2026.10.21.

## 2026.10.19 — 2026-10-22

[Index page](https://tiles.salishsea.io/2026.10.19/index.html) · [Changes](https://github.com/salish-sea/basemap/compare/2026.10.18...2026.10.19)

- Parks over 1 km across are named at their headquarters (a visitor centre, ranger station or office) rather than at any point inside them. Deception Pass State Park's name no longer sits in its quiet north end ([decision 026](decisions/026-parks-are-named-at-their-headquarters-and-reserves-tinted-on-the-land.md)).
- Nature reserves that are named as parks, about 545 of them, are tinted as parks on the land they cover. This includes many Washington state parks, which OpenStreetMap maps as nature reserves. Other reserves, such as state forests and wildlife areas, are not tinted.
- Peninsulas are named, from a zoom that depends on their size: Key, Kitsap and Miller Peninsulas had no names before ([decision 023](decisions/023-peninsulas-are-named-from-a-zoom-set-by-their-size.md)).
- Where labels collide, natural features such as islands now win over towns, and cities win over both, so a park's name no longer takes an island's place ([decision 024](decisions/024-natural-features-are-named-before-towns-and-cities-before-them.md)). Ketron Island is no longer labelled twice.
- The map uses OpenStreetMap data from Protomaps' build of 2026-10-22.

## 2026.10.18 — 2026-10-21

[Index page](https://tiles.salishsea.io/2026.10.18/index.html) · [Changes](https://github.com/salish-sea/basemap/compare/2026.10.17...2026.10.18)

- The image tiles are no longer drawn blank. About 190 of 2026.10.17's 63,935 image tiles were squares of plain background colour; none are now.
- The map uses OpenStreetMap data from Protomaps' build of 2026-10-21. This is the first version built on Hostess ([decision 021](decisions/021-full-builds-run-on-hostess.md)).

## 2026.10.17 — 2026-10-20

[Index page](https://tiles.salishsea.io/2026.10.17/index.html) · [Changes](https://github.com/salish-sea/basemap/compare/2026.10.16...2026.10.17)

- Washington's salmon labels are now whole river systems, labelled where each reaches the sea. The Duwamish, Black and Green labels at Tukwila used to appear at different zooms, and the Black's disappeared as you zoomed in ([decision 020](decisions/020-each-river-mouth-is-labelled-with-its-salmon-runs.md)).

## 2026.10.16 — 2026-10-19

[Index page](https://tiles.salishsea.io/2026.10.16/index.html) · [Changes](https://github.com/salish-sea/basemap/compare/2026.10.15...2026.10.16)

- Shipping lanes are fainter: outlines at 30% strength with precautionary areas dashed, arrows at half strength from zoom 10, names from zoom 12, and the separation zones no longer drawn. They had been the boldest thing on the water after the sightings ([decision 019](decisions/019-shipping-lanes-are-drawn-from-the-charts.md)).
- The Skeena, Nass, Stikine, Taku and Alsek are labelled with their salmon runs. The Peace and the Columbia, which reach the sea outside British Columbia, still are not.

## 2026.10.15 — 2026-10-19

[Index page](https://tiles.salishsea.io/2026.10.15/index.html) · [Changes](https://github.com/salish-sea/basemap/compare/2026.10.14...2026.10.15)

- Shipping lanes are drawn from NOAA's and Fisheries and Oceans Canada's charts, on the map but not in the image tiles ([decision 019](decisions/019-shipping-lanes-are-drawn-from-the-charts.md)).
- Each named river that reaches the sea is labelled at its mouth with the salmon and steelhead runs it carries, from WDFW, NWIFC and Fisheries and Oceans Canada ([decision 020](decisions/020-each-river-mouth-is-labelled-with-its-salmon-runs.md)).
- Islets that OpenStreetMap tags only as islets are labelled, such as Ben Ure and Deception Islands at Deception Pass, and so are named islands too small for Protomaps to label.
- Named forests are no longer labelled, because in Washington most are timberland named for its owner ([decision 016](decisions/016-points-of-interest-are-where-people-watch-from.md)).

## 2026.10.14 — 2026-10-19

[Index page](https://tiles.salishsea.io/2026.10.14/index.html) · [Changes](https://github.com/salish-sea/basemap/compare/2026.10.13...2026.10.14)

- Each version has an index page that links all of its files, and a GitHub release that links the page. The image tiles, place lists and archives are named for their contents, so their addresses cannot be guessed from a version number. The README lists the newest version's files.
- In the OpenStreetMap place list, a place that shares its name with another now says which island it is on. SalishSea.io's search used to put the Cattle Point on San Juan Island "near Lopez Island".

## 2026.10.13 — 2026-10-16

[Changes](https://github.com/salish-sea/basemap/compare/2026.10.12...2026.10.13)

- The place lists hold the Salish Sea's larger places, about 2,200, in place of the 17,725 names the whole coast labels: water and points labelled by zoom 12, islands that fit at zoom 13, and cities, towns, villages and ferry terminals. They shrink from 272 KB to 32 KB gzipped ([decision 018](decisions/018-the-names-the-map-labels-are-published-as-lists.md)).
- There is one ferry terminal for each landing the map's routes reach, named as most records name it: 218 OpenStreetMap records, which included berths and foot ramps, become 92 landings.

## 2026.10.12 — 2026-10-16

[Changes](https://github.com/salish-sea/basemap/compare/2026.10.11...2026.10.12)

- Each version now publishes two JSON lists of the places the map labels, so a site can search them: water bodies and points from the government gazetteers, and OpenStreetMap's islands, towns and ferry terminals. They are separate because their licences differ. The style names them in its metadata as `salishsea:places` ([decision 018](decisions/018-the-names-the-map-labels-are-published-as-lists.md)).
- Islets and small islands, which Protomaps files under points of interest and never draws, are labelled from the zoom Protomaps gives each.

## 2026.10.11 — 2026-10-15

[Changes](https://github.com/salish-sea/basemap/compare/2026.10.10...2026.10.11)

- Depth labels are set in Noto Serif and drawn level rather than turned along their lines. A serif 1 stands on its foot at any angle, so 150 m no longer reads as 750 m ([decision 017](decisions/017-depth-labels-are-set-in-a-serif.md)). The serif's glyphs are served with the other fonts from tiles.salishsea.io.

## 2026.10.10 — 2026-10-15

[Changes](https://github.com/salish-sea/basemap/compare/2026.10.9...2026.10.10)

- Depth labels are set in Noto Sans Regular instead of Italic, so a 1 stands upright. This did not fully work, and 2026.10.11 replaces it.

## 2026.10.9 — 2026-10-15

[Changes](https://github.com/salish-sea/basemap/compare/2026.10.8...2026.10.9)

- Points of interest are limited to where people watch from: beaches, parks, forests, peaks, marinas, ferry terminals, aerodromes, museums and zoos, plus benches, toilets and drinking water at the closest zooms. Restaurants, cafes, shops and schools along the waterfront are no longer drawn ([decision 016](decisions/016-points-of-interest-are-where-people-watch-from.md)).

## 2026.10.8 — 2026-10-15

[Changes](https://github.com/salish-sea/basemap/compare/2026.10.7...2026.10.8)

- Landmarks are drawn from zoom 11: lighthouses, the landmarks the charts mark, and tall radio towers, with their own icons. They win over bay and depth labels where they collide ([decision 015](decisions/015-landmarks-are-what-the-charts-mark-and-tall-towers.md)).

## 2026.10.7 — 2026-10-14

[Changes](https://github.com/salish-sea/basemap/compare/2026.10.6...2026.10.7)

- This is the first published version with image tiles, for sites that stitch tiles into a picture, such as profile maps and preview cards. They are drawn from the style without its labels, in 256-pixel tiles each drawn at 512 pixels. They cover zooms 0 to 5 over the coarse map, 6 to 10 over the coast and a little past it, and 11 to 15 only along the Salish Sea's shore. A version's style names them under `salishsea:images` ([decision 014](decisions/014-image-tiles-are-drawn-from-the-style-along-the-shore.md)).
- The tiles stay in Web Mercator ([decision 013](decisions/013-the-tiles-are-in-web-mercator.md)).

## 2026.10.6 — 2026-10-14

[Changes](https://github.com/salish-sea/basemap/compare/2026.10.5...2026.10.6)

- This version was never published. Its changes, which made Chromium start on the build machine and changed when image tiles are redrawn, are in 2026.10.7.

## 2026.10.5 — 2026-10-14

[Changes](https://github.com/salish-sea/basemap/compare/2026.10.4...2026.10.5)

- The coarse map now has land. 2026.10.4 had its seafloor but no land.

## 2026.10.4 — 2026-10-14

[Changes](https://github.com/salish-sea/basemap/compare/2026.10.3...2026.10.4)

- A coarse map of the Northeast Pacific (180 to 90°W) lies under the detailed coast, so a map can zoom out or pan past the coast's edges without a blank. The relief no longer shades a cliff along the coast's edge ([decision 012](decisions/012-a-coarse-map-covers-the-northeast-pacific.md)).

## 2026.10.3 — 2026-10-14

[Changes](https://github.com/salish-sea/basemap/compare/2026.10.2...2026.10.3)

- The detailed coast is widened to 136 to 120°W and 36 to 54.8°N, to cover everywhere SalishSea.io takes killer whale sightings from ([decision 011](decisions/011-the-coast-covers-salishsea-ios-data.md)).

## 2026.10.2 — 2026-10-14

[Changes](https://github.com/salish-sea/basemap/compare/2026.10.1...2026.10.2)

- The style's fonts and icons are served from tiles.salishsea.io, not from Protomaps' site, so a page that uses the map needs to allow only that one site ([decision 010](decisions/010-fonts-and-icons-are-served-with-the-tiles.md)).

## 2026.10.1 — 2026-10-14

- The first version, published at tiles.salishsea.io as a MapLibre style with vector tiles. The sea is tinted by depth bands, with depth contours labelled at their depths, from Canada's depth grid where it has data and NOAA's elsewhere, and GEBCO in the deep ocean ([decision 001](decisions/001-canadas-depth-grid-comes-first.md), [decision 009](decisions/009-gebco-fills-the-deep-ocean.md)). Ground that dries at low tide is drawn as mud flats ([decision 004](decisions/004-ground-that-dries-at-low-tide-is-drawn.md)).
- Relief is shaded in the browser by MapLibre from elevation tiles ([decision 002](decisions/002-the-relief-is-shaded-by-maplibre.md)). Land is one flat colour except parks, which are tinted green ([decision 003](decisions/003-land-is-flat-except-parks.md)). Rivers are blue from zoom 9 and streams from zoom 13, and fade into the sea's tint by zoom 12.
- Named passenger ferry routes are drawn from zoom 9, as one line per channel up to zoom 12 and as mapped from zoom 13 ([decision 005](decisions/005-ferry-routes-are-drawn-from-zoom-9.md)).
- Names of bays, straits, channels and points come from the US and Canadian government gazetteers, moved toward open water and turned along it, with the Canada-US boundary at sea drawn as a grey dash and dot ([decision 006](decisions/006-marine-names-and-the-boundary-come-from-government-gazetteers.md)).
- Published versions are numbered in CalVer and never change once published ([decision 007](decisions/007-published-builds-are-dated-and-never-change.md)). Versions share unchanged archives, so each file is stored once.
