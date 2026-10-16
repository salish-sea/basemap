# 018 — The names the map labels are published as lists a site can search

**Status:** accepted · **Decided:** 2026-10-16, by Peter

## Context

SalishSea.io will let people search for a place by name and go to it on the map. The names it needs are on the basemap, but only as labels inside vector tiles, which a browser draws and can't search. Those names come from two places. The names of the water and of points on it come from the two national gazetteers, placed by [scripts/names.py](../scripts/names.py) ([decision 006](006-marine-names-and-the-boundary-come-from-government-gazetteers.md)). Islands, towns and ferry terminals come from OpenStreetMap, through Protomaps' tiles.

## Decision

**Each version publishes the names the map labels as two lists, kept apart because their licences differ** ([scripts/places.py](../scripts/places.py)):

- `places-gazetteers.json` holds the water bodies and points that `names.py` chose, at the positions and from the zooms the map labels them. US names are in the public domain, and Canadian names are under the Open Government Licence – Canada.
- `places-osm.json` holds islands and islets, cities, towns, villages, hamlets, suburbs and neighbourhoods, and ferry terminals, from OpenStreetMap, under the ODbL.

**Only kinds the map labels are listed.** Peter chose this over two wider lists. One would have added everything in the gazetteers near salt water, such as beaches, rocks and summits. The other would have held every name in the region.

**Each place gives a position to look at and a zoom to look from.** For a water body or a point, that is where the map writes its label and the zoom from which it does. For an island drawn as an outline, it is the middle of the outline and the zoom at which the whole island fills about one 512-pixel tile. For a town or a ferry terminal, it is OpenStreetMap's point, at a zoom set by its kind: 11 for a city, down to 15 for a neighbourhood or a ferry terminal. Other names that OpenStreetMap records, such as `alt_name`, `short_name` and `official_name`, go with the place, so that a search for Salt Spring Island finds Saltspring Island.

**Each list is one JSON object.** It says what the list holds, its sources, its licence and the attribution it needs, then names its columns (`name`, `kind`, `lon`, `lat`, `zoom`, `other_names`) and gives its places as rows, which keeps the file small. Over the test window, the two lists hold about 2,000 places and are about 30 KB gzipped.

**A version's style names the lists in its metadata, as `salishsea:places`,** as it names its image tiles ([decision 014](014-image-tiles-are-drawn-from-the-style-along-the-shore.md)). Like the archives, each list is stored once under a name made from its contents (`places/places-osm-<hash>.json`), so a version that doesn't change the names shares the earlier version's lists.

**No list of aliases.** Sighting reports shorten names, such as EDM for Edmonds and "Jeff Head" for Jefferson Head. Peter's view is that the abbreviations keep reports brief and that people don't expect them to work in a search field. "Jeff Head" and "edm" should find their places because each word starts a word of the name, and that is for the search to do, not the list.

## Rejected

- **Everything near salt water**, adding the gazetteers' beaches, rocks, reefs, bars and summits. Many of these places have no label on the map, so a search would go to an unmarked spot.
- **Every name in the region.** About half of the gazetteers' names around the Salish Sea are creeks, lakes, swamps and glaciers. In Washington alone, OpenStreetMap names over 5,000 parks and 3,000 peaks.
- **Reading the names out of the tiles.** A label is repeated in every tile it touches and is cut at the tiles' zooms, so the list would have to be rebuilt from the pieces. The sources the tiles were made from are already in the build.
- **One list.** The OpenStreetMap names are under the ODbL, which this project keeps apart from the public-domain and open-government data ([README](../README.md#what-it-is-built-from)).
- **Orcapelago's hand-kept list of aliases.** It is not ours to publish, and per Peter its abbreviations aren't search terms.

## Known problems

- Many places share a name, such as the several Mud Bays. The lists give no county or island to tell them apart. A site can name the nearest town or island from the lists themselves.
- The zoom for a town or a ferry terminal is set by its kind, not by the zoom at which Protomaps first draws its label, which also depends on population.
- OpenStreetMap's islands include islands in lakes and rivers.
- Parks, beaches, peaks and the landmarks ([decision 015](015-landmarks-are-what-the-charts-mark-and-tall-towers.md)) are labelled on the map but not listed.
