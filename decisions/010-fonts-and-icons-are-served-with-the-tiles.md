# 010 — The fonts and icons are served with the tiles

**Status:** accepted · **Decided:** 2026-10-14

## Context

A MapLibre style names two more things besides its tiles: the glyphs its labels are drawn with, one file per font and block of 256 characters, and a sprite, the sheet of icons for places such as parks and airports. The style is built on Protomaps' layers, which use three fonts, Noto Sans Regular, Medium and Italic, and Protomaps' "light" icons. Until now the style fetched both from Protomaps' own copy on GitHub Pages, `protomaps.github.io/basemaps-assets`.

That made every map that uses tiles.salishsea.io depend on a second site, which can change or go away without notice, and it meant SalishSea.io's content security policy would have had to allow that site too.

## Decision

**The fonts and icons are copied from Protomaps' [basemaps-assets](https://github.com/protomaps/basemaps-assets) repository at one commit, and served from tiles.salishsea.io** under a path named for that commit, such as `assets/basemaps-assets-028c18f713ba/`. Like a version, that path never changes: a different commit gets a different path, so every published style keeps the fonts and icons it was drawn with.

- **The style names the commit** ([style/style.ts](../style/style.ts), `ASSETS_COMMIT`); the Makefile reads it from there to fetch the files into `build/assets/`, and [scripts/publish.sh](../scripts/publish.sh) to upload them. A publish sends them only if they aren't in the bucket yet: about 13 MB the first time, nothing after.
- **Only what the style uses is copied:** the three fonts and the light icons, not the repository's other fonts and colour schemes.
- **The licences go with them:** the fonts' SIL Open Font Licence, and the MIT licence of [tangrams/icons](https://github.com/tangrams/icons), which Protomaps' icons are drawn from.
- **The comparison page draws a local build with the local copy,** so it, and the README's pictures, need nothing from tiles.salishsea.io.

## Rejected

- **Keep fetching them from Protomaps' site.** It costs nothing, but it is a dependency on someone else's hosting that nobody here would notice breaking, and it would widen SalishSea.io's content security policy.
- **Build our own glyphs** with MapLibre's font-maker, from the Noto fonts. It would give a choice of fonts and characters, but Protomaps' files are made that way already, from the same fonts, and nothing here needs anything they lack.
