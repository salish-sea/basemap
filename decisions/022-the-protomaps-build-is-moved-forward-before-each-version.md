# 022 — The Protomaps build is moved forward before each version

**Status:** accepted · **Decided:** 2026-10-20, by Peter

## Context

Most of what the map draws on land, from roads to coastlines, comes from Protomaps' daily build of the planet. The Makefile pins one build by its date, `PROTOMAPS_BUILD`, and extracts the region from it at build.protomaps.com.

Protomaps keeps only about a week of daily builds. On 2026-10-20 the pin was still `20261013`: that build and the next day's answered 404, and those from 2026-10-15 on answered 200. The Fly machine never noticed, because its volume kept the extract it had made on 2026-10-14, but the first build on hostess ([021](021-full-builds-run-on-hostess.md)) failed at its first step. It went ahead only with that extract copied off the volume.

## Decision

**The pin stays, and is moved to the newest daily build before each version is built for publishing,** in its own commit. A pin names exactly which build a version drew from, and the settings record that the extract depends on includes it, so changing it is what makes a build extract again.

So a version's land is at most a few days older than OpenStreetMap when it is built, and a pin is never more than about a week from being impossible to rebuild.

## Rejected

- **Keeping each pinned extract ourselves**, in the cache or in the bucket beside the archives. Each is about 2.2 GB for the coast, and keeping them would let the map's land fall behind OpenStreetMap for as long as nobody moved the pin.
- **Following Protomaps' newest build without a pin.** A version would no longer say which build it drew from, and since the settings record wouldn't change, a machine that already had an extract would keep using it.
