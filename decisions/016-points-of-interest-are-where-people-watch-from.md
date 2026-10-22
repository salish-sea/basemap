# 016 — Points of interest are where people watch from, not businesses

**Status:** accepted; amended 2026-10-19 and 2026-10-22 · **Decided:** 2026-10-15 · **Context:** Peter, looking at SalishSea.io's map after it moved to this basemap

## Context

Protomaps' style draws a `pois` layer: 36 kinds of place from OpenStreetMap, each with an icon and a name, from a zoom that depends on the place. Most of them are businesses and town amenities: restaurants, cafés, bars, supermarkets, convenience stores, bookshops, beauty salons, electronics and clothes shops, post offices, schools, libraries, a town hall, a theatre. Kept as Protomaps ships it, the layer filled the waterfront of a town such as Friday Harbor with restaurant names. Peter's verdict was that "Ferry Noodle House is not a point of interest. It is a business." Esri's ocean basemap, which SalishSea.io used before, had none of them.

What a person placing a whale sighting uses is where they were watching from and what they could see: a beach, a park, a marina, a ferry terminal, a peak.

## Decision

**The `pois` layer keeps these kinds and drops the rest** ([style/style.ts](../style/style.ts), `POI_KINDS`):

- **where people watch from:** beach, park, nature reserve and peak;
- **what they set out from or can see:** marina, ferry terminal and aerodrome, which includes seaplane bases;
- **museum and zoo**, for the Whale Museum in Friday Harbor and Point Defiance Zoo & Aquarium;
- **bench, toilets and drinking water**, which help someone choose a spot to watch from. Protomaps' tiles hold them back to zoom 17, or 16 if named, so they appear only when the map is zoomed right in, and most have no name. The style can't keep only the ones near a beach, so they are kept everywhere.

Everything else Protomaps draws in that layer is left out. (Amended 2026-10-19, by Peter: `forest` was kept at first, on the guess that a named forest is usually a park or reserve. In Washington it is mostly timberland named for its owner, such as "Rayonier Forest Resources", "Snoqualmie Forest" and "BTG Pactual", well away from the water, and the parks people watch from are kept as `park`. Forests are left out.) (Amended 2026-10-16: the layer's islets and small islands, the kind `coastline`, which Protomaps' style never draws, are drawn by a layer of their own as island names, not as points of interest; see [decision 018](018-the-names-the-map-labels-are-published-as-lists.md).) (Amended 2026-10-22, by Peter: `nature_reserve` is kept. OpenStreetMap tags many Washington state parks as nature reserves rather than parks, such as Deception Pass, Moran, Fort Casey, Larrabee and Miller Peninsula State Parks, so none of them had a name. Protomaps' style gives the kind no icon and no colour, so the name would be drawn in the background's colour; reserves are drawn as parks are, with the park's icon and green. Over the test window they add 338 names to about 1,900 parks; some are inland, such as Burns Bog, which the style can't tell apart. They are drawn by a layer of their own, below the islands' names, so that a reserve covering an island, as Kukutali Preserve covers Kiket Island, gives way to the island's name.) The layer's other conditions, such as the zoom each place first appears at, are Protomaps' own and unchanged. The style replaces only the list of kinds, and if a future Protomaps release changes the shape of the layer's filter, building the style fails rather than silently drawing everything.

## Rejected

- **Keeping Protomaps' list.** Businesses come and go and say nothing about where a sighting was.
- **Dropping the layer.** Beaches, parks and ferry terminals are how people describe where they watched from, and nothing else on the map names a marina or a ferry terminal.
- **Keeping `attraction`.** It holds whale-watching companies and outreach centres, such as Western Prince Whale Watching and the Orca Survey Outreach & Education Center in Friday Harbor, but also every other tourist attraction. The whale-related ones are businesses or not places to watch from.

## Known problems

- A park named for its island takes the island's name's place, as Hope Island Marine State Park does Hope Island's: the points of interest are placed before the islands' names. Reserves are placed after them (amended 2026-10-22), but parks were left as they were.
- A city's benches are kept too, at the closest zoom.
