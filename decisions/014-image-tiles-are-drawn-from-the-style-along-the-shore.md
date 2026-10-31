# 014 — Image tiles are drawn from the style, without labels, and close in only along the shore

**Status:** accepted · **Decided:** 2026-10-14 · **Carries out:** SalishSea.io's [074](https://github.com/salish-sea/salishsea-io/blob/main/docs/decisions/074-the-basemap-is-its-own-project-and-the-cards-draw-on-it.md), which planned image tiles beside the vector tiles

*Amended 2026-10-30:* where Chromium has a graphics card, it draws the tiles on it, through EGL ([scripts/images.ts](../scripts/images.ts)), and in software only where it has none. On hostess's Quadro P4000, in Docker, a sample of 5,361 of the coast's tiles took 50 s, 106 a second, against 532 s in software; at that rate the whole coast's 63,935 tiles would take about 10 minutes rather than 95. The card's tiles differ from the software renderer's by half a step in 255 on average, about what the WebP compression does, and the most different look the same side by side at three times their size. Changing renderer changes every tile's bytes once, so the first version drawn on the card uploads a new set. [builder/run.sh](../builder/run.sh) passes the card to the container once Docker has been told of it (CONTRIBUTING, "Publishing").

## Context

Three things in SalishSea.io stitch image tiles into a picture rather than draw a map: the profile pages' maps, which are prerendered as SVG with each tile an `<image>`; the ecotype page's small maps, built the same way; and the preview cards, which a Lambda composites from tiles. All three still use Esri's World Ocean Base tiles, and each carries Esri's attribution. They ask for tiles at these zooms, counted in 256-pixel tiles, as Esri's are:

- the preview cards at 8 and 9, centred anywhere SalishSea.io has data;
- the small maps at 8, over the Salish Sea;
- a profile map at whatever zoom fits its reports, up to 10;
- a seal haul-out's profile map at about 15, because its 500 m radius fills the picture at that zoom. SalishSea.io has 362 haul-outs, all between 125.2°W and 122.2°W and between 47.1°N and 50.0°N.

## Decision

**The tiles are drawn by MapLibre GL, in headless Chromium, from the map's own style** ([viewer/images.html](../viewer/images.html), driven by [scripts/images.ts](../scripts/images.ts)), so a picture looks like the map beside it. The style is the map's without its symbol layers: no labels, no icons and no road shields. A label near a tile's edge would be cut off in one tile and drawn whole, or not at all, in the next, which in a stitched picture shows as half a word. Esri's ocean base had no labels either.

**Each tile is 256 pixels in the zoom numbering, drawn at 512**, for high-density screens. A tile at zoom *z* shows what the map shows at MapLibre's zoom *z* − 1, whose tiles are 512 pixels. The tiles are drawn in blocks of up to 4 by 4, in the middle of a map one tile wider on every side, so the relief at a block's edge is shaded from the ground beyond it and the blocks meet without a seam. They are WebP, at quality 0.85, about 12 KB each. A block during which any tile failed to load, or that takes over two minutes, is drawn again on a fresh page, and after three tries the build stops, so a hole is never published.

**The tiles drawn** ([scripts/image_tiles.py](../scripts/image_tiles.py)):

- zooms 0 to 5 over the coarse map's area, 180–90°W and 15–70°N ([012](012-a-coarse-map-covers-the-northeast-pacific.md));
- zooms 6 to 10 over the coast ([011](011-the-coast-covers-salishsea-ios-data.md)) and three tiles beyond it, because a picture framed on a sighting near the coast's edge reaches past it;
- zooms 11 to 15 only along the shore, inside 125.5–122°W and 47–50.5°N. A tile is on the shore if it holds both land and sea by OpenStreetMap's coastline, the one the map draws, or if the depth grid in it goes below sea level and comes within 5 m of the surface: seals haul out on rocks and reefs that OpenStreetMap leaves out and the 30 m grid puts a metre or two under water. Around each shore tile at zoom 15 go two tiles either side and one above and below, because a haul-out's picture, 720 by 384 pixels, is 2.8 tiles wide and 1.5 high; at zooms 11 to 14, the tiles holding those and a ring around them. Checked against SalishSea.io's haul-outs in the test window around Haro Strait, every picture finds all its tiles but those of eight sites whose catalogue positions are a degree of longitude east of the places they name (SalishSea.io's `salish-3zok.17`). A site added later on the same shore is covered too.

**They are stored once, under a name made from their contents,** as the archives are ([007](007-published-builds-are-dated-and-never-change.md)): `images/<hash>/{z}/{x}/{y}.webp`, with the list of tiles uploaded last, as `tiles.txt`, as the sign that the set is complete. A version's style names its set in its metadata, as `salishsea:images`, a URL with `{z}`, `{x}` and `{y}` in it. A version whose tiles are the same as the last one's shares them.

**Drawing them is slow,** about 7 tiles a second on a laptop with Chromium's software renderer; the test window has 18,000 of them. So they are a separate step, `make images`, which a full build runs before publishing ([021](021-full-builds-run-on-hostess.md)).

## Rejected

- **Drawing zooms 11 to 15 everywhere in the Salish Sea.** That is 207,000 tiles, most of them inland or open water, for pictures that only ever look at the shore.
- **Drawing close-ups only around SalishSea.io's haul-outs.** About 14,000 tiles, but the basemap would read SalishSea.io's catalogue, and a haul-out added later would have no close-up until the next build.
- **Drawing tiles when they are first asked for,** on a server. That is a service to keep running, to answer for pictures that are few enough to draw ahead of time.
- **MapLibre Native,** the renderer written in C++. It is faster, but it is a second renderer that lags MapLibre GL's style features, the hillshade's newer settings among them, so the pictures would drift from the map.
- **Keeping the labels.** See above.

## Known problems

- A picture that asks for a close-up away from the shore, or outside the area above, gets no tiles at zooms 11 to 15. SalishSea.io's pictures don't.
