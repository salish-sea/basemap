# 005 — Ferry routes are drawn from zoom 7, one line per channel

**Status:** accepted · **Decided:** 2026-10-13, by Peter

## Context

Many casual sightings are made from ferries, and reports place whales by the ferry lanes. In 3,976 sighting reports from 2026, about 280 mention a ferry and about 100 a lane, as in "south of the Edmonds–Kingston ferry lanes" or "west of the ferry lane near Vashon side". Esri's ocean basemap, which SalishSea.io uses today, draws ferry routes as dashed lines. Ours drew none: Protomaps' light style has no ferry line layer, and Protomaps' tiles carry ferry routes only from zoom 12.

Where several routes share a channel, such as the Washington State Ferries routes from Anacortes through the San Juan Islands, OpenStreetMap maps each route separately, a few hundred metres apart. Drawn dashed side by side, they look like rope.

## Decision

**Ferry routes are drawn as a dashed slate line from zoom 7, and named along the line from zoom 11.** Slate keeps them apart from the blue isobaths.

**Up to zoom 12, routes that share a channel are drawn as one line;** from zoom 13, each route is drawn as mapped. Routes within 300 m of each other count as sharing a channel. [scripts/ferries.py](../scripts/ferries.py) takes the routes longest first, and each later route keeps only its parts outside the earlier ones, joined back to the line it leaves from. Labels always come from the separate routes, so every route keeps its name.

**The routes come from the Protomaps extract,** read at zoom 13, where each OpenStreetMap way's pieces are joined back up across tile edges. They go into an archive of our own OpenStreetMap layers, `osm.pmtiles`, kept apart from the depth data under the ODbL like the extract itself. The short approaches to ferry berths are left out.

## Known problems

- Where two routes run parallel just over 300 m apart, both are drawn, as briefly near Lopez Sound.
- Ferry terminals are drawn by Protomaps as points from zoom 13 or so; ferry docks are among the places reports name most, so they may want labels earlier.
