# 016 — Points of interest are where people watch from, not businesses

**Status:** accepted · **Decided:** 2026-10-15 · **Context:** Peter, looking at SalishSea.io's map after it moved to this basemap

## Context

Protomaps' style draws a `pois` layer: 36 kinds of place from OpenStreetMap, each with an icon and a name, from a zoom that depends on the place. Most of them are businesses and town amenities: restaurants, cafés, bars, supermarkets, convenience stores, bookshops, beauty salons, electronics and clothes shops, post offices, schools, libraries, a town hall, a theatre. Kept as Protomaps ships it, the layer filled the waterfront of a town such as Friday Harbor with restaurant names. Peter's verdict was that "Ferry Noodle House is not a point of interest. It is a business." Esri's ocean basemap, which SalishSea.io used before, had none of them.

What a person placing a whale sighting uses is where they were watching from and what they could see: a beach, a park, a marina, a ferry terminal, a peak.

## Decision

**The `pois` layer keeps these kinds and drops the rest** ([style/style.ts](../style/style.ts), `POI_KINDS`):

- **where people watch from:** beach, park, forest (a named forest is usually a park or reserve) and peak;
- **what they set out from or can see:** marina, ferry terminal and aerodrome, which includes seaplane bases;
- **museum and zoo**, for the Whale Museum in Friday Harbor and Point Defiance Zoo & Aquarium;
- **bench, toilets and drinking water**, which help someone choose a spot to watch from. Protomaps' tiles hold them back to zoom 17, or 16 if named, so they appear only when the map is zoomed right in, and most have no name. The style can't keep only the ones near a beach, so they are kept everywhere.

Everything else Protomaps draws in that layer is left out. (Amended 2026-10-16: the layer's islets and small islands, the kind `coastline`, which Protomaps' style never draws, are drawn by a layer of their own as island names, not as points of interest; see [decision 018](018-the-names-the-map-labels-are-published-as-lists.md).) The layer's other conditions, such as the zoom each place first appears at, are Protomaps' own and unchanged. The style replaces only the list of kinds, and if a future Protomaps release changes the shape of the layer's filter, building the style fails rather than silently drawing everything.

## Rejected

- **Keeping Protomaps' list.** Businesses come and go and say nothing about where a sighting was.
- **Dropping the layer.** Beaches, parks and ferry terminals are how people describe where they watched from, and nothing else on the map names a marina or a ferry terminal.
- **Keeping `attraction`.** It holds whale-watching companies and outreach centres, such as Western Prince Whale Watching and the Orca Survey Outreach & Education Center in Friday Harbor, but also every other tourist attraction. The whale-related ones are businesses or not places to watch from.

## Known problems

- A city's benches are kept too, at the closest zoom.
