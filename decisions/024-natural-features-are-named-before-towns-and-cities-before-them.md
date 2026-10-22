# 024 — Natural features are named before towns, and cities before them

**Status:** accepted · **Decided:** 2026-10-22, by Peter

## Context

Where two labels would overlap, MapLibre draws the one in the layer higher in the style and leaves the other out. Protomaps' style puts the names of points of interest, roads and towns above the islands' names, and our style had kept that order, adding its peninsulas' names beside the islands' ([decision 023](023-peninsulas-are-named-from-a-zoom-set-by-their-size.md)). So:

- at zooms 12 and 13, Hope Island Marine State Park's name took the place of Hope Island's;
- from zoom 12, the name of Wright Bliss Road Northwest took Key Peninsula's place;
- at zoom 9.4, the towns' names crowded out Haro Strait's.

Peter's view: natural features should typically have higher priority, and the island itself is more important than a park named after it.

## Decision

**Labels win their places in this order,** first to last ([style/style.ts](../style/style.ts)):

1. countries' names and the rivers' salmon runs (decision 020);
2. cities, which Protomaps marks as `kind_detail` `city`, such as Vancouver, Victoria, Bremerton and Saanich;
3. the names of water bodies that appear by zoom 9: straits, sounds, inlets and the biggest bays (decision 006);
4. the names of islands, islets and peninsulas;
5. towns, villages and hamlets, such as Silverdale, Sidney and Eastsound, then regions and neighbourhoods;
6. landmarks, then points of interest (decisions 015 and 016), then major roads' names, then lakes and the open sea;
7. the names of smaller bays and of points, then ferry routes, depths and shipping lanes, and last minor roads' names.

Hope Island is now named at zooms 12 and 13, where the park's name gives way, and both fit from 14. Key Peninsula keeps its name at 12, and Haro Strait is named at 9.4. At zoom 8, Bainbridge Island and Vashon Island are named where the towns of Silverdale and Vashon were.

## Rejected

- **Natural features before everything, cities included.** Tried first: Vancouver lost its name at zoom 7 to Burrard Peninsula, Victoria at 10 to Esquimalt Peninsula, and Bremerton at 8 to Kitsap Peninsula.
- **Protomaps' order.** It loses the names in Context above.

## Known problems

- The split between cities and towns is Protomaps', from OpenStreetMap: Langford, of 47,000 people, is a city and wins against a peninsula, while Silverdale, of 21,000, is a town and doesn't.
- Miller Peninsula's name is gone at zoom 9, where Discovery Bay's runs through its place, and back at 10.
