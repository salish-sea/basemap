# 002 — The relief is shaded by MapLibre, from elevation tiles

**Status:** accepted · **Decided:** 2026-10-13, by Peter · **Amends:** SalishSea.io's [073](https://github.com/salish-sea/salishsea-io/blob/main/docs/decisions/073-the-basemap-depths-are-30-m-lightly-shaded.md), which baked the relief into image tiles

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

**MapLibre shades the relief from elevation tiles.** The style sets its strength (about half), its light and its fade between z11.5 and z13. The image tiles for SalishSea.io's preview cards and small maps are rendered from the same style ([074](https://github.com/salish-sea/salishsea-io/blob/main/docs/decisions/074-the-basemap-is-its-own-project-and-the-cards-draw-on-it.md)), so they get the same relief.

What shading costs on a slow phone has not been measured yet (bd `salish-3zok`).

## Rejected

- **Relief baked into image tiles.** It is five times the archive, and every change to how the relief looks needs a rebuild.
