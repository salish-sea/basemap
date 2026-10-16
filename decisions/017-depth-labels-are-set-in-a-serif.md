# 017 — Depth labels are set in a serif, so a 1 doesn't read as a 7

**Status:** accepted · **Decided:** 2026-10-16 · **Context:** SalishSea.io's `salish-3zok.19`

## Context

The isobaths are labelled with their depth, "100 m", along the line and turned to follow it, in the italic blue of the sea's names ([006](006-marine-names-and-the-boundary-come-from-government-gazetteers.md)). Noto Sans's 1 has a long flag and no foot. On a line that climbs to the right, the flag turns nearly flat, and the 1 reads as a 7. Off Tramp Harbor at zoom 13, the 100 m and 150 m isobaths read "700 m" and "750 m", where the water is nowhere near that deep. The data was right; the labels misled.

## Decision

**Depth labels are set in Noto Serif Regular,** at the same size and colour, with the same halo, still turned along their lines. A serif 1 stands on a foot, so it reads as a 1 at any angle. Depths are the only labels in a serif face, which sets them apart from names as soundings are set apart on a chart.

**The serif is served with Protomaps' fonts.** A MapLibre style names one place for all its fonts, so a published version's fonts are Protomaps' three ([010](010-fonts-and-icons-are-served-with-the-tiles.md)) and the serif together, under `assets/fonts-<hash>/`, named for their contents ([scripts/publish.sh](../scripts/publish.sh)). Only the serif's first block of 256 characters is built, because a depth is digits, a space and "m": one 87 KB file, checked in at [style/fonts/](../style/fonts/) and made by [scripts/serif_glyphs.sh](../scripts/serif_glyphs.sh) from the Noto project's font at one commit, checked against its hash. The Makefile puts both in `build/fonts/`, which the comparison page serves too.

The image tiles have no labels, so their style still names Protomaps' fonts alone and is unchanged.

## Rejected

- **Upright Noto Sans, turned along the line** (2026.10.10). It fixes the lean of italics but not the turn: on the same line off Tramp Harbor, "150 m" still read as "750 m".
- **Level labels, placed on their lines but not turned** (built, not published). Every depth read correctly, but on a steep shore the labels of neighbouring isobaths overlap one another when level, so MapLibre leaves most of them out: off Lime Kiln, the nearshore depths disappeared.
- **Noto Sans Mono,** whose 1 has a foot too. It is wider, and off Tramp Harbor the 150 m label no longer fit along its line.
- **Noto Sans Medium, or a larger size.** Neither changes the flag's angle, and a larger label fits fewer stretches of line.
