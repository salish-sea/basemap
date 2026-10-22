# 023 — Peninsulas are named, from a zoom set by their size

**Status:** accepted · **Decided:** 2026-10-22, by Peter

## Context

Peter noticed that Key Peninsula and Miller Peninsula had no names on the map, nor had any other peninsula, though they are among the larger shapes of Puget Sound's shore.

Protomaps' tiles do hold them, but only as points of interest of the kind `peninsula`, each from zoom 12 whatever its size, and Protomaps' style never draws that kind. Around the Salish Sea there are 14 of them, from Bailey Peninsula on Lake Washington to the Olympic Peninsula. A name from zoom 12 suits Davison Head on San Juan Island, but the Olympic Peninsula is then many tiles across and its name a small mark somewhere in the mountains.

The government gazetteers list peninsulas too, as points: GNIS files Key Peninsula as a cape, at a point inland near Vaughn, and Canada's names database lists about fifty, most on the outer coast. A point says where a peninsula is, but not how big it is.

## Decision

**Peninsulas are named from OpenStreetMap's outlines, from a zoom set by their size.** [scripts/peninsulas.py](../scripts/peninsulas.py) writes every named `natural=peninsula`, at the point inside its outline furthest from its edge, from two zooms before the outline fits one tile, when it spans about a quarter of one. That is the rule the islets follow ([decision 018](018-the-names-the-map-labels-are-published-as-lists.md)). It gives the Olympic and Kitsap Peninsulas from zoom 6, Key Peninsula from 7, Miller, Quimper and Saanich Peninsulas from 8, and Davison Head from 12. A peninsula mapped only as a point is named from 12, as Protomaps gives every peninsula. Over the whole coast that is 35 names.

**They are drawn as the islands' names are,** in grey italic ([style/style.ts](../style/style.ts), `peninsula_labels`), and where they collide they give way to towns' names, points of interest and the names of the larger water bodies, as Kitsap Peninsula's does to Bremerton and Silverdale at zoom 8. They ride in the landmarks' archive, OpenStreetMap's like the islets, whose tiles now start at zoom 6 rather than 9. Everything else in it carries its own first zoom, from 9 on, so the lower zooms hold only peninsulas. Protomaps' peninsula points are left undrawn, so no peninsula is named twice. The image tiles have no labels and are unchanged.

## Rejected

- **Protomaps' points, from zoom 12.** A change to the style alone, and the first one offered, but the large peninsulas would be named only once the map is zoomed far past them.
- **The gazetteers' points.** They hold no size, so every peninsula would appear at one zoom, and Key Peninsula's GNIS point lies about 9 km south of the widest part of its outline, where its name sits.

## Known problems

- Burrard Peninsula, in Vancouver, is named twice from zoom 12: OpenStreetMap maps it as an outline named "Burrard Peninsula" and as a point named "Burrard Peninsula / Ulxen", and the two names don't match.
- Peninsulas aren't in the lists of places a search offers (decision 018).
- A peninsula's name gives way to other names as the map is zoomed in, and doesn't come back: [scripts/label_sweep.ts](../scripts/label_sweep.ts), run with `--layer=peninsula_labels`, finds Key Peninsula's drawn from zoom 8 to 11 and gone at 12, where the name of Wright Bliss Road Northwest runs through its place, and Bayocean Peninsula's gone at 10, Granville Island's at 13 and Mosley Island's at 14. By then each is wider than its name.
