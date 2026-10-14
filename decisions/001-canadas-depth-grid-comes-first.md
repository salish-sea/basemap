# 001 — Canada's depth grid is used wherever it has data

**Status:** accepted · **Decided:** 2026-10-13, by Peter · **Amends:** SalishSea.io's [073](https://github.com/salish-sea/salishsea-io/blob/main/docs/decisions/073-the-basemap-depths-are-30-m-lightly-shaded.md), which split the grids at 49°N

## Context

The basemap's depth bands, isobaths and relief come from one 30 m elevation grid stitched from several sources (073). As first decided, Natural Resources Canada's West Coast topo-bathymetric DEM was used north of 49°N and west of 127°W, and NOAA's Coastal Relief Model Volume 8 south of 49°N.

The first build, over Haro Strait, showed two problems with that split. Shaded side by side, NOAA's grid has straight seams where its survey patches meet, in the Strait of Georgia south of 49°N and in Haro Strait. NRCan's grid has no seams there and otherwise matches NOAA's. The split also left a visible step in the relief along the border. NRCan's grid reaches south of 49°N, to a straight edge at about 48.06°N. That takes in the Strait of Juan de Fuca, Haro Strait, the San Juan Islands and the north end of Admiralty Inlet, but not Puget Sound, Hood Canal or the Washington coast.

## Decision

**NRCan's grid is used wherever it has data, resampled from 10 m to 30 m. NOAA's grids fill in everywhere else:** south of about 48.06°N, Puget Sound included, and anywhere offshore that NRCan's grid doesn't reach.

**Each grid keeps its own vertical datum.** NOAA's CRM Volumes 7 and 8 give heights above EGM2008, which is close to mean sea level. NRCan's metadata says its elevations were "re-calculated to the vertical chart datum used by the Canadian Hydrographic Service", a low-water level. So NRCan's depths read a little shallower. Over Haro Strait, NRCan's grid is shallower by a median of 1.1 m in water NOAA puts at 0–10 m deep, and by 1.9 m in water 100–400 m deep. That moves the shallow isobaths slightly where the grids meet, and nautical charts measure depth from a low-water level too. The coastline comes from OpenStreetMap, not from either grid (073), so it doesn't move.

The build passes `-novshift` to `gdalwarp`. Without it, `gdalwarp` converts NOAA's EGM2008 heights to heights above the ellipsoid, because the target CRS has no vertical datum, and NOAA's depths come out about 20 m too deep.

## Known problems

- Where NRCan's grid ends, at about 48.06°N and 122.2°W, a straight seam showed in the relief, across Discovery Bay, Indian Island and Admiralty Inlet. Since 2026-10-13 the two grids are blended over 4 km inside NRCan's edge ([scripts/mosaic.py](../scripts/mosaic.py)), which hides it, and spreads out the 1–2 m difference between their datums.

## Rejected

- **Converting NRCan's grid to EGM2008, for now.** It would remove the 1–2 m step where the grids meet. The Canadian Hydrographic Service publishes surfaces that relate its chart datum to the ellipsoid, which could do it, but the step is smaller than the gap between the shallowest bands (5 m), so it isn't worth the work yet.
- **Keeping the split at 49°N.** It keeps NOAA's seams in US waters and adds a step along the border.
