# 002 — The relief is shaded by MapLibre, from elevation tiles

**Status:** accepted · **Decided:** 2026-10-13, by Peter · **Amends:** SalishSea.io's [073](https://github.com/salish-sea/salishsea-io/blob/main/docs/decisions/073-the-basemap-depths-are-30-m-lightly-shaded.md), which baked the relief into image tiles

*Amended 2026-10-21:* what shading costs on a phone was measured on Peter's Galaxy S22, a 2022 flagship (Snapdragon 8 Gen 1, Android 15, Chrome 144, a 1080×2340 screen at three device pixels per CSS pixel, drawing at 60 Hz), with SalishSea.io's own style and map settings: panning 500 px over four seconds at zooms 9, 10 and 11 over Haro Strait, then zooming from 9 to 11. With the relief, every pan and zoom ran at 60 frames a second, and not one of 10,084 frames took over 50 ms; the first full render took 1.7 s (the median of six runs) against 1.1 s without it (five runs). With Chrome's developer tools slowing the page's processor four times, as a stand-in for a mid-range phone (the slowing is uneven on Android: a busy loop ran 1.1 to 2.9 times slower), panning ran at 56 frames a second with the relief and 57 without, zooming at 52 and 57, the worst runs at 45 and 49, and the first full render took 1.9 s against 1.4 s. So the relief costs about half a second on first render and nothing measurable in frame rate; a few frames a second on a processor four times slower. Neither fallback considered when this was decided (a lower maxzoom for the elevation tiles, or no relief below some device class) is needed. The phone bounds the fast end of older Android phones, not the slow end. The measurements and the harness are recorded in SalishSea.io's bd `salish-3zok.5`.

## Context

The relief is the light and shadow of the seafloor and land, drawn under roads and labels and faded out before it would blur. As first decided (073), the build computed it and baked it into translucent image tiles, and the style set only its opacity.

The first build, over Haro Strait, compared that with MapLibre's `hillshade` layer, which shades the relief in the browser from tiles that hold elevations (Mapzen's Terrarium encoding). For that window:

| | Baked into image tiles | Shaded by MapLibre |
|---|---|---|
| Archive | 96 MB, to z12 | 18 MB, to z11 |
| Look | A little crisper at z11.5–12, from its extra zoom level | Softer |
| Changing how it looks | A rebuild | A style edit |

Elevations are rounded to a quarter of a metre, which halves the archive. Rounded to a whole metre, flat seafloor shows ripples like contour lines.

## Decision

**MapLibre shades the relief from elevation tiles.** The style sets its strength (a quarter, lowered from a half by Peter after the first build), its light and its fade between z11.5 and z13. The image tiles for SalishSea.io's preview cards and small maps are rendered from the same style ([074](https://github.com/salish-sea/salishsea-io/blob/main/docs/decisions/074-the-basemap-is-its-own-project-and-the-cards-draw-on-it.md)), so they get the same relief.

What shading costs on a phone was measured on 2026-10-21: see the amendment above.

## Rejected

- **Relief baked into image tiles.** It is five times the archive, and every change to how the relief looks needs a rebuild.
