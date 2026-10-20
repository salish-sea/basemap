# 020 — Each named river that reaches the sea is labelled at its mouth with its salmon and steelhead runs

**Status:** accepted; amended 2026-10-20 · **Decided:** 2026-10-19, by Peter · **Rights:** SalishSea.io's rights policy §7.3, D-24

## Context

Resident killer whales follow salmon. Someone who sees whales off a river's mouth may wonder whether the fish are why, and which fish. The map named the rivers but said nothing about what runs in them.

Both governments publish which salmon use which streams. Washington's [SWIFD](https://geodataservices.wdfw.wa.gov/arcgis/rest/services/MapServices/SWIFD/MapServer/0), the Statewide Washington Integrated Fish Distribution, is kept by WDFW with the Northwest Indian Fisheries Commission for the western Washington treaty tribes. It records each run (spring, summer or fall Chinook; odd- or even-year pink; summer or winter steelhead) on each stream reach, and whether the fish spawn, rear or are present there. British Columbia's [NuSEDS](https://open.canada.ca/data/en/dataset/c48669a3-045b-400d-b730-48aafe8c5ee6), Fisheries and Oceans Canada's salmon spawner database, places each salmon population at the mouth of its stream, with the stream's provincial watershed code. Peter's [rights determination](https://github.com/salish-sea/salishsea-io/blob/main/docs/rights-policy.md#73-which-salmon-run-in-which-river-wdfw-and-nwifcs-swifd-and-dfos-nuseds-d-24) (D-24): the runs per river are facts and may be used, credited; neither dataset is republished.

## Decision

**Each named river system that reaches the sea gets a label at its mouth: its name, and under it the runs of all its streams** ([scripts/salmon.py](../scripts/salmon.py), [style/style.ts](../style/style.ts), `salmonLayer`), for example:

> **Skagit River**
> Chinook (spring, summer, fall) · coho · chum (fall) · pink (odd years) · sockeye · steelhead (summer, winter)

- **Which rivers.** Those Protomaps' tiles name at zoom 10, whose names end in River, Creek, Stream or Brook. A delta's channels, such as Hat Slough or West Pass, are part of their river. A river has to reach salt water: a tributary's mouth, such as the Sauk's on the Skagit, isn't where whales would be.
  - In Washington, a river is a system built from SWIFD's own lines (amended 2026-10-20, below). Each stream flows out at its end near the sea, or else its lower end by the depth grid, and into the stream that end touches, unless that stream ends at the same point too, as the Black does beside the Green. A stream ending away from the sea and any stream, as the Cedar's route does across Lake Washington, flows into the nearest stream within 1 km: the Cedar into the Ship Canal. A stream whose line is clipped where it meets the sea, as SWIFD's lines run on across harbors, is an outlet of its own. The system is labelled where its outlet reaches the sea, which is within about 3 km of Protomaps' marine water: the sea, which Protomaps tells from a lake, as the depth grid can't, Lake Washington's bed being below sea level in it. A river whose line runs on across the sea for more than 40 km, as the Columbia's does past Longview, is labelled at its bar. The system is named for the named river nearest its outlet, and where several are equally near, for all of them, longest first: "Cedar and Sammamish Rivers" at the Ballard Locks. Systems of one name with mouths within 15 km of each other are one, as the Skagit's forks are.
  - In British Columbia, a river is its watershed code, so two streams of one name are two rivers, and it reaches the sea when its code is a single group for a great river that reaches the sea (the Fraser's `100`, the Skeena's `400`, the Nass's `500`, the Stikine's `600`, the Taku's `700`) or a coastal drainage's own river in the 900s (the Alsek's `990`), or one level below a coastal drainage, as the Cowichan's, `920-252823`, is. (Amended 2026-10-20: 2026.10.15 accepted only the Fraser's single group, and so missed the Skeena.) The Harrison, `100-077501`, is a tributary. The depth grid can't tell these apart there, because it records the Fraser's channel below sea level.
- **Which runs.** In Washington, the runs SWIFD documents on any of the system's streams: seen there, including hatchery fish and fish carried past a dam, but not presumed, modelled or historic. So the Duwamish lists the Green's and the Black's. In British Columbia, every population in the river's watershed, by its code, so the Fraser lists the runs of the Harrison, the Adams and the rest. NuSEDS doesn't hold steelhead, so British Columbia's rivers don't list them.
- **When.** In Washington, by how many kilometres of a system's streams SWIFD records salmon on: from zoom 10 for at least 900 (the Columbia's 17,000, the Skagit's 4,800, the Duwamish's 1,100), 11 for at least 100 (the Skokomish, the Dungeness), and 12 for less. In British Columbia, by the river's length on the map: 10 for at least 40 km, 11 for 12 km, and 12 for a creek.
- **How.** The river's name in the medium weight and its runs beneath, small, in a muted river blue. The labels are placed before the towns' names, because a town often stands at a river's mouth, as Cowichan Bay does at the Cowichan's, and the runs are the point of the label there; the town's name gives way. They are labels, so the image tiles leave them out.
- **Where they're kept.** In the landmarks' archive, with the islets' names. Which rivers are labelled follows OpenStreetMap's names, so the labels are kept with its data under the ODbL.
- **Credit.** "Salmon runs: WDFW and NWIFC, Fisheries and Oceans Canada", in the map's attribution.
- **Fetched once**, into a folder named for the date (the Makefile's `SALMON_DATE`), and again only when the date changes.

Over the test window, 27 rivers are labelled; over Washington and the British Columbia shore beside it, 84.

**Amended 2026-10-20, by Peter: Washington's rivers are systems.** As published in 2026.10.15 and 2026.10.16, each Washington stream SWIFD names was labelled at its stream identifier, read as its mouth, if the depth grid found the sea nearby. The Green, the Black and the Duwamish, which meet at Tukwila, were three labels there, ten kilometres from Elliott Bay, because the dredged Duwamish Waterway is deep in the grid; each appeared at its own zoom, and as Peter zoomed in, the Black's gave way to the Duwamish's. SWIFD's identifiers turned out not to be mouths at all: the Duwamish River's is halfway along it. The Cedar and the Sammamish were labelled out in Lake Washington, whose bed the grid holds below sea level. Building systems from SWIFD's lines puts one label where each system reaches the sea.

**Before a release, the labels are swept for collisions** ([scripts/label_sweep.ts](../scripts/label_sweep.ts)): each is centred on the map and zoomed from its first zoom to 15, and MapLibre says whether it was drawn. A label drawn and then not drawn has lost its place to another, which no picture at one zoom shows. On 2026.10.16 the sweep finds the Black River's and the Cedar River's labels lost at zoom 12; on this change, none of the 84.

## Rejected

- **Every stream with a run.** Thousands of creeks, most of them inland and none named on the map at the zooms people look at.
- **Run timing by month,** as a calendar. The run names already carry the season, and a calendar needs more room than a label has.
- **Current run sizes,** as Zoe Liu's Orca Salmon Dashboard shows for two counting sites. A different question, and SalishSea.io's `salish-q90` carries it.
- **A layer of the site's own**, drawn by SalishSea.io rather than the basemap. The labels describe the rivers the basemap draws, and Orcasound's map would want them too.
- **Placing the labels after the towns' names.** At the Cowichan, the label found no room and wasn't drawn.

## Known problems

- British Columbia's rivers don't list steelhead.
- The Elwha appears only from zoom 12: SWIFD documents salmon on just 45 km of it.
- Which way a stream flows is read from the depth grid when neither end is near the sea, and a stream across a lake or a flat could be read the wrong way round.
- The sweep checks the basemap's own labels; SalishSea.io's viewpoints and sightings, drawn above them, take their place by design.
- A town's name at a river's mouth is hidden while the river's label is shown.
