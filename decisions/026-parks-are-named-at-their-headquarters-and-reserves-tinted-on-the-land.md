# 026 — Parks are named at their headquarters, and nature reserves tinted on the land

**Status:** accepted · **Decided:** 2026-10-22, by Peter

## Context

Peter noticed that Deception Pass State Park was named at the far north of the park, where people rarely go, that Miller Peninsula State Park's name seemed placed at random, and that American Camp was tinted green while Washington's state parks were not.

Protomaps puts each park's name at a point it computes to lie somewhere inside the park's outline (`pointOnSurface` in its [`Pois.java`](https://github.com/protomaps/basemaps/blob/main/tiles/src/main/java/com/protomaps/basemap/layers/Pois.java)), with no regard for where people go. Deception Pass State Park is six pieces on both sides of the pass, and its name landed north of the pass, by Pass Lake. Its headquarters, by Cranberry Lake, is where people think of the park as being.

The tint was [decision 003](003-land-is-flat-except-parks.md)'s: parks and national parks, not nature reserves, because some reserves' outlines reach over the sea, as Boundary Bay's does, and the style can't trim a fill to the land. OpenStreetMap tags many state parks as nature reserves, among them Deception Pass, Miller Peninsula, Moran and Larrabee, so they had no tint, and their names floated over plain land.

## Decision

**Protomaps still decides which parks are named, of what kind and from which zoom; we decide where.** [scripts/parks.py](../scripts/parks.py) reads Protomaps' points of the kinds park, national park and nature reserve, finds each one's outline in OpenStreetMap, by its name and Protomaps' point lying inside it, and moves the name:

1. to the park's headquarters, office, ranger station or visitor centre, if one lies inside the outline, preferring one whose name includes the park's, as "Deception Pass State Park Headquarters" does;
2. otherwise to the point of the park's land furthest from its edges, as for Miller Peninsula State Park.

A park with no outline in OpenStreetMap keeps Protomaps' point. Over the coast that is 22,526 names: 551 at a headquarters, 20,678 in the middle of their land and 1,297 where Protomaps put them. The names are drawn as Protomaps draws its points of interest, as parks, from the landmarks' archive; Protomaps' own park points are left undrawn, and national parks are named now as well.

**Nature reserves named as parks are tinted as parks are, from their outlines less the sea,** read from Protomaps' tiles at zoom 13. Over the coast there are 3,550 nature reserves, but only about 545 are named as parks: state, provincial, regional and county parks. The rest are wildlife areas, conservancies, natural areas, wildernesses and state forests, and Peter chose to leave them flat, as decision 003 leaves land that isn't a park. Capitol State Forest, near Olympia, is timberland. The outlines ride in the archive of our own OpenStreetMap layers, which the image tiles are drawn from, so the image tiles show them too.

## Rejected

- **Copying Protomaps' rules for which parks are named and from which zoom.** They are dozens of rules on tags and areas, and a slip would change which parks show at each zoom; reading Protomaps' own points keeps its choices exactly.
- **Tinting every nature reserve.** Tried first: it tinted state forests and watersheds, and wildlife areas over farmland, as green as the parks.
- **A headquarters only when its name includes the park's.** It would miss most ranger stations, which are unnamed or named "Ranger Station" or "Park Office". Peter judged a visitor centre a good place too, even a town's inside a town park, as the Port Angeles Visitor's Center is inside City Pier.

## Known problems

- Two parks that overlap can have their middles close together, so that only one is named: Boundary Bay Regional Park and Boundary Bay Wildlife Management Area both lie along the bay's dyke, and the regional park, where people go, loses its name to the management area's.
- Moran State Park is named at the Summit Visitor Center on Mount Constitution, not by Cascade Lake, where its campgrounds are.
- A park along a trail, such as the Galloping Goose Regional Trail, is named at whatever visitor centre lies on it.
- Reading every park point from Protomaps' most detailed tiles takes about 8 minutes over the coast, and the sea at zoom 13 another minute and a half.
- The sea at zoom 13 is a little coarser than the shore at zoom 15, so a reserve's tint can stop a few metres short of the shore, or run a few metres past it, when the map is zoomed right in.
