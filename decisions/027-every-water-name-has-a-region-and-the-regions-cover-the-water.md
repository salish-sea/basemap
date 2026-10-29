# 027 — Every water name the map labels has a region, and the regions cover the water

**Status:** proposed: the regions are agreed (Peter, 2026-10-28, over five rounds of review); their licence, and so which archive and list they go in, is not

## Context

SalishSea.io wants to say where a sighting was in words, "Port Madison, off Point Jefferson", rather than only as a dot ([salish-sea/salishsea-io](https://github.com/salish-sea/salishsea-io), bd `salish-fwyt.2`). A name is a point in both gazetteers ([006](006-marine-names-and-the-boundary-come-from-government-gazetteers.md)), and a point can't say which water a sighting was in. Canada's names database (CGNDB) outlines about a third of its marine names, and NOAA's charts outline named sea areas for US waters, but neither divides the sea: their outlines nest (Penn Cove inside Saratoga Passage inside Puget Sound), leave gaps, cut one inlet into pieces at each chart's edge, and omit most small bays. No ready-made division exists, from either country or from the monitoring programs.

Peter, 2026-10-27: "the place needs its own layer, built for this purpose, that assigns all water to a named region". He reviewed five rounds of it drawn over the map (https://desktop-wsl.tail5d2e45.ts.net/place-names/, on his tailnet) and settled the rules below.

## Decision

**Every water name the map labels has one region, which holds its label, and the regions together cover the water:** every point at sea is in exactly one. "If it's labeled on the map, it should have a place name" (Peter), with the exceptions below. The regions are built by [scripts/regions.py](../scripts/regions.py) from what the map itself is drawn from, at about 90 m, over 42°N to 51.5°N and out to 129°W: the Salish Sea and the coasts its whales use. Beyond that a site can say "off Alaska" or "off California" itself; the whole coast at this grid needs five times the memory.

- **Water** is the depth grid below zero, and ground that dries at low tide ([004](004-ground-that-dries-at-low-tide-is-drawn.md)), less OpenStreetMap's land. Humpbacks forage over the flats (Peter); and the Skagit's and Fraser's diked farmland lies below the grid's zero.
- **A name that either source outlines near its label takes that outline's water,** every piece and chart scale merged. Where outlines nest, the smallest wins.
- **A name with only a point takes the water its shore encloses:** the land is grown until the bay's mouth closes, what is then cut off is filled, and the land is shrunk back, trying mouths up to about 3 km wide, smallest first, so a cove stops at its own mouth and an open bay closes across its headlands. **A channel, passage or reach**, or a bay reports name or the map labels from zoom 11, that encloses nothing takes the water near its label that lies no farther from land than the label does: a narrow channel's width, a strip along an open bay's beach.
- **All other water joins the nearest region, measured through the water,** never across land. On the outer coast, open water more than 1.5 km from a name's own is "off Vancouver Island", "off the Washington coast" or "off Oregon"; finer division there doesn't matter to the whales that enter the Salish Sea (Peter).
- **Each region reaches about 300 m onto the shore beside it,** after the water is all taken, so it never crosses a spit. Many sightings of nearshore animals are placed where the observer stood (Peter), and 492 sightings within a kilometre of the Ballard Locks fall in Shilshole Bay rather than between grid cells.
- **Neighbours' edges are smoothed together,** so they still meet.

**Some labelled names are no region:** coves and bights, unless sighting reports name them (Penn Cove; the names reports use, with how often, are a checked-in list, [regions-known.tsv](../regions-known.tsv), counted from SalishSea.io's published reports and refreshed by hand), as "too small for note" (Peter); a chart's navigation ranges; fresh water, for now (Salmon Bay above the locks, Lake Washington's bays: Peter, "might want it later"); and a point with no water of its own that no report names. Their water joins their neighbours'. **A short hand-kept list,** [regions-overrides.json](../regions-overrides.json), each entry with who asked and why, drops a few more (Hogum Bay: "pretty far offshore to be a bay"), merges East Oro Bay into Oro Bay, and renames one of two Narrows "Tacoma Narrows".

**A name that several regions share is told apart as a card would say it,** by whichever reads better (Peter): an island or town within 2 km ("Mud Bay (Sucia Island)"), else the larger water it opens onto ("Rocky Bay (Case Inlet)"), else the nearest island or town, else by hand ("The Narrows (Tahuya)", "Maple Bay (Sansum Narrows)", the latter rather than an Indigenous village's name chosen by rule).

**The regions are a layer of `marine.pmtiles`, `regions`, drawn by the style only when a page asks for it,** so that SalishSea.io can show them for review, and **a list a site can read beside the place lists**, so its read-path build can name each sighting's water.

## Rejected

- **The two gazetteers' outlines as they come.** Eld Inlet came out as four pieces that didn't cover it, Rocky Bay's label lay outside Rocky Bay, and Hammersley Inlet, Andrews Bay and Westcott Bay had no outline at all.
- **The monitoring programs' basins** (WDFW's bird-survey basins for PSEMP, Ecology's Salish Sea Model basins): too coarse for a card, US waters only, and without a licence stated. They may yet group regions into basins.
- **A disc of water around each label without an outline.** It drew circles out into open water (Rolling Bay, Baynes Channel).
- **Names that only appear in reports' text.** Reports rarely name water: "Puget Sound" appears 38 times in 30,450 reports with text. They name points and islands, which a sighting's landmark, not its region, will say.

## Known problems

- The grid is about 90 m: a channel narrower than that, or fresh water above sea level, is land to it.
- A coast bay neither source outlines is found from its point alone, which a bay as long as Willapa Bay defeats: its sub-bays then share its water.
- 81 regions come out in more than one piece of half a square kilometre or more, mostly in British Columbia's inlets.
