# 020 — Each named river that reaches the sea is labelled at its mouth with its salmon and steelhead runs

**Status:** accepted · **Decided:** 2026-10-19, by Peter · **Rights:** SalishSea.io's rights policy §7.3, D-24

## Context

Resident killer whales follow salmon. Someone who sees whales off a river's mouth may wonder whether the fish are why, and which fish. The map named the rivers but said nothing about what runs in them.

Both governments publish which salmon use which streams. Washington's [SWIFD](https://geodataservices.wdfw.wa.gov/arcgis/rest/services/MapServices/SWIFD/MapServer/0), the Statewide Washington Integrated Fish Distribution, is kept by WDFW with the Northwest Indian Fisheries Commission for the western Washington treaty tribes. It records each run (spring, summer or fall Chinook; odd- or even-year pink; summer or winter steelhead) on each stream reach, and whether the fish spawn, rear or are present there. British Columbia's [NuSEDS](https://open.canada.ca/data/en/dataset/c48669a3-045b-400d-b730-48aafe8c5ee6), Fisheries and Oceans Canada's salmon spawner database, places each salmon population at the mouth of its stream, with the stream's provincial watershed code. Peter's [rights determination](https://github.com/salish-sea/salishsea-io/blob/main/docs/rights-policy.md#73-which-salmon-run-in-which-river-wdfw-and-nwifcs-swifd-and-dfos-nuseds-d-24) (D-24): the runs per river are facts and may be used, credited; neither dataset is republished.

## Decision

**Each named river that reaches the sea gets a label at its mouth: its name, and under it its runs** ([scripts/salmon.py](../scripts/salmon.py), [style/style.ts](../style/style.ts), `salmonLayer`), for example:

> **Skagit River**
> Chinook (spring, summer, fall) · coho · chum (fall) · pink (odd years) · sockeye · steelhead (summer, winter)

- **Which rivers.** Those Protomaps' tiles name at zoom 10, whose names end in River, Creek, Stream or Brook. A delta's channels, such as Hat Slough or West Pass, are part of their river. A river has to reach salt water: a tributary's mouth, such as the Sauk's on the Skagit, isn't where whales would be.
  - In Washington, a mouth reaches the sea when the ground within 300 m of it is no higher than 5 m and water within 8 km is at least 1 m deep, by the depth grid. That passes the Snohomish and fails the Bear Creeks, whose mouths are 90 m up. A river that ends at the head of its delta, as the Skagit does at Conway, is labelled at the mouth of a fork that reaches the sea, with the forks' runs and its own together. A fork is its river's only if its mouth is within 15 km of the river's, so that a North Fork Bear Creek isn't taken for a fork of every Bear Creek.
  - In British Columbia, a river is its watershed code, so two streams of one name are two rivers, and it reaches the sea when its watershed code is the Fraser's, `100`, or one level below a coastal drainage, as the Cowichan's, `920-252823`, is. The Harrison, `100-077501`, is a tributary. The depth grid can't tell these apart there, because it records the Fraser's channel below sea level.
- **Which runs.** In Washington, the runs SWIFD documents anywhere on the river's own stream: seen there, including hatchery fish and fish carried past a dam, but not presumed, modelled or historic. A run present on the main stem is usually passing through to spawn upstream, which is the fact that matters at the mouth. In British Columbia, every population in the river's watershed, by its code, so the Fraser lists the runs of the Harrison, the Adams and the rest. NuSEDS doesn't hold steelhead, so British Columbia's rivers don't list them.
- **When.** From zoom 10 for a river at least 40 km long on the map, 11 for one at least 12 km, and 12 for a creek.
- **How.** The river's name in the medium weight and its runs beneath, small, in a muted river blue. The labels are placed before the towns' names, because a town often stands at a river's mouth, as Cowichan Bay does at the Cowichan's, and the runs are the point of the label there; the town's name gives way. They are labels, so the image tiles leave them out.
- **Where they're kept.** In the landmarks' archive, with the islets' names. Which rivers are labelled follows OpenStreetMap's names, so the labels are kept with its data under the ODbL.
- **Credit.** "Salmon runs: WDFW and NWIFC, Fisheries and Oceans Canada", in the map's attribution.
- **Fetched once**, into a folder named for the date (the Makefile's `SALMON_DATE`), and again only when the date changes.

Over the test window, 29 rivers are labelled.

## Rejected

- **Every stream with a run.** Thousands of creeks, most of them inland and none named on the map at the zooms people look at.
- **Run timing by month,** as a calendar. The run names already carry the season, and a calendar needs more room than a label has.
- **Current run sizes,** as Zoe Liu's Orca Salmon Dashboard shows for two counting sites. A different question, and SalishSea.io's `salish-q90` carries it.
- **A layer of the site's own**, drawn by SalishSea.io rather than the basemap. The labels describe the rivers the basemap draws, and Orcasound's map would want them too.
- **Placing the labels after the towns' names.** At the Cowichan, the label found no room and wasn't drawn.

## Known problems

- British Columbia's rivers don't list steelhead.
- SWIFD's runs are those on a river's own stream. A run that spawns only in a tributary and isn't recorded on the main stem is missed.
- Washington's test for reaching the sea uses the depth grid near the mouth, and a mouth on a bluff above its beach could fail it, as Salt Creek's nearly did.
- A town's name at a river's mouth is hidden while the river's label is shown.
