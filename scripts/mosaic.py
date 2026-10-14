# /// script
# requires-python = ">=3.12"
# dependencies = ["rasterio>=1.4", "numpy>=2", "scipy>=1.13"]
# ///
"""Combine depth grids into one, each laid over the ones before it and blended at its edges.

The grids are given in order of preference, least preferred first, all on the same
1-arc-second lattice (the Makefile warps them there): for the whole coast, GEBCO's global
grid for the deep ocean, then NOAA's Coastal Relief Model volumes, then Canada's grid
(decisions/001, 009). Each grid is used wherever it has data, except within RAMP metres of
the edge of its data, where it is mixed with what lies beneath: all the grid beneath at
the edge, all this grid RAMP inside it. Without that, every edge would leave a step,
because the grids measure from different levels and were built from different surveys;
the clearest was the straight seam where Canada's grid ends, at about 48.06°N.

The work is done in blocks, each read with a margin as wide as the ramp, so the whole
area is never in memory. The output also holds averaged copies at 1/2, 1/4 … 1/256 of
its resolution (GDAL's overviews), so the zoomed-out elevation tiles can be cut without
reading the whole grid (scripts/elevation_tiles.py).
"""

import argparse
import math
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import Window
from scipy import ndimage

BLOCK = 2048
NODATA = -99999.0

_args: argparse.Namespace | None = None


def _blend(job: tuple[int, int]) -> tuple[Window, np.ndarray]:
    row, col = job
    sources = [rasterio.open(path) for path in _args.grids]
    try:
        first = sources[0]
        height, width = first.height, first.width
        core = Window(col, row, min(BLOCK, width - col), min(BLOCK, height - row))
        # Cell size on the ground at this block's latitude, for measuring the ramp.
        lat = first.xy(row + core.height // 2, col)[1]
        dy = abs(first.transform.e) * 111320
        dx = first.transform.a * 111320 * math.cos(math.radians(lat))
        pad_r, pad_c = math.ceil(_args.ramp / dy), math.ceil(_args.ramp / dx)
        r0, c0 = max(0, row - pad_r), max(0, col - pad_c)
        r1, c1 = min(height, row + core.height + pad_r), min(width, col + core.width + pad_c)
        outer = Window(c0, r0, c1 - c0, r1 - r0)

        out = np.full((outer.height, outer.width), NODATA, dtype=np.float32)
        have = np.zeros(out.shape, dtype=bool)
        for src in sources:
            grid = src.read(1, window=outer, masked=True)
            has = ~np.ma.getmaskarray(grid)
            if not has.any():
                continue
            values = grid.data.astype(np.float32)
            under = has & have
            if under.any() and not has.all():
                # Metres from each cell with this grid's data to the nearest cell without.
                inside = ndimage.distance_transform_edt(has, sampling=(dy, dx))
                w = np.clip(inside[under] / _args.ramp, 0, 1).astype(np.float32)
                values[under] = w * values[under] + (1 - w) * out[under]
            out[has] = values[has]
            have |= has
    finally:
        for src in sources:
            src.close()

    inner = (slice(row - r0, row - r0 + core.height), slice(col - c0, col - c0 + core.width))
    return core, out[inner]


def _init(args: argparse.Namespace) -> None:
    global _args
    _args = args


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("output", help="GeoTIFF to write")
    p.add_argument("grids", nargs="+", help="grids on the output lattice, least preferred first")
    p.add_argument("--ramp", type=float, default=4000, help="metres over which each grid is blended in")
    args = p.parse_args()

    with rasterio.open(args.grids[0]) as first:
        profile = first.profile
        height, width, transform = first.height, first.width, first.transform
    for path in args.grids[1:]:
        with rasterio.open(path) as src:
            if (src.width, src.height, src.transform) != (width, height, transform):
                raise SystemExit(f"{path} is not on the same lattice as {args.grids[0]}")
    profile.update(
        driver="GTiff", dtype="float32", nodata=NODATA, count=1, tiled=True, blockxsize=512,
        blockysize=512, compress="deflate", predictor=3, bigtiff="if_safer", num_threads="all_cpus",
    )

    jobs = [(r, c) for r in range(0, height, BLOCK) for c in range(0, width, BLOCK)]
    # Blocks are handed out a few at a time, so finished ones can't pile up in memory
    # faster than they're written.
    batch = 2 * (os.cpu_count() or 1)
    # A worker the kernel kills for lack of memory fails the run (BrokenProcessPool),
    # where multiprocessing.Pool would wait for it forever.
    with rasterio.open(args.output, "w", **profile) as dst, ProcessPoolExecutor(initializer=_init, initargs=(args,)) as pool:
        for i in range(0, len(jobs), batch):
            for window, data in pool.map(_blend, jobs[i:i + batch]):
                dst.write(data, 1, window=window)
    with rasterio.open(args.output, "r+", num_threads="all_cpus") as dst:
        dst.build_overviews([2 ** i for i in range(1, 9)], Resampling.average)
    print(f"{args.output}: {len(jobs)} blocks from {len(args.grids)} grids")


if __name__ == "__main__":
    main()
