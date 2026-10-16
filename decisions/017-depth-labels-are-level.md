# 017 — Depth labels are level, so a 1 doesn't read as a 7

**Status:** accepted · **Decided:** 2026-10-16 · **Context:** SalishSea.io's `salish-3zok.19`

## Context

The isobaths are labelled with their depth, "100 m", along the line and turned to follow it, in the italic blue of the sea's names ([006](006-marine-names-and-the-boundary-come-from-government-gazetteers.md)). Noto Sans's 1 has a long flag. On a line that climbs to the right, the flag turns nearly flat, and the 1 reads as a 7. Off Tramp Harbor at zoom 13, the 100 m and 150 m isobaths read "700 m" and "750 m", where the water is nowhere near that deep. The data was right; the labels misled.

## Decision

**Depth labels are drawn level and upright,** in Noto Sans Regular, at the same size and colour and with the same halo. Each is still placed on its line, where the line has room for it, but it no longer turns with the line, so a 1 always stands up. The names of bays, straits and the sea stay italic and follow their shapes, because they are words.

On a steep shore, where the isobaths crowd together, a level label finds room less often than one turned along its line, so fewer depths are labelled there. The lines are all still drawn.

## Rejected

- **Upright type turned along the line.** This was 2026.10.10, the first attempt. It fixes the lean of italics but not the turn: on the same line off Tramp Harbor, "150 m" still read as "750 m".
- **Noto Sans Medium, or a larger size.** Neither changes the flag's angle. A larger size also no longer fits along short stretches of line, and the labels there disappear.
