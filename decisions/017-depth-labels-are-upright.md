# 017 — Depth labels are upright, so a 1 doesn't read as a 7

**Status:** accepted · **Decided:** 2026-10-16 · **Context:** SalishSea.io's `salish-3zok.19`

## Context

The isobaths are labelled with their depth along the line, "100 m", in the italic blue of the sea's names ([006](006-marine-names-and-the-boundary-come-from-government-gazetteers.md)). In Noto Sans Italic, a 1 leans and has a long flag. Turned to follow a line that runs up to the right, it reads as a 7. Off Tramp Harbor at zoom 13 the 100 m and 150 m isobaths read "700 m" and "750 m", where the water is nowhere near that deep. The data was right; the labels misled.

## Decision

**Depth labels are set in Noto Sans Regular,** at the same size and colour, with the same halo. A 1 stands upright and reads as a 1 at any angle the line takes. The names of bays, straits and the sea stay italic, as maps set water names, because they are words.

## Rejected

- **Noto Sans Medium.** It reads a little more clearly still, but it makes the depths heavier than every other label on the map.
- **A larger size.** At 11 px, a label no longer fits along short stretches of line, and MapLibre leaves it out: the 100 m label off Tramp Harbor disappeared.
