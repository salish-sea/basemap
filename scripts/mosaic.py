# /// script
# requires-python = ">=3.12"
# dependencies = ["rasterio>=1.4", "numpy>=2", "scipy>=1.13"]
# ///
"""Combine NOAA's and Canada's depth grids into one, blending where Canada's ends.

Both inputs are on the same 1-arc-second lattice (the Makefile warps them there).
Canada's grid is used wherever it has data (decisions/001), but where its data ends, as
along its straight southern edge at about 48.06°N, switching to NOAA's would leave a
step: the two grids measure from different levels and were built from different
surveys. So within RAMP metres of the edge of Canada's data, the two are mixed, from
all NOAA at the edge to all Canada RAMP inside it. Where only one grid has data, that
one is used.

The work is done in blocks, each read with a margin as wide as the ramp, so the whole
area is never in memory.
"""

import argparse
import math
import multiprocessing as mp

import numpy as np
import rasterio
from rasterio.windows import Window
from scipy import ndimage

BLOCK = 2048
NODATA = -99999.0

_args: argparse.Namespace | None = None


def _blend(job: tuple[int, int]) -> tuple[Window, np.ndarray]:
    row, col = job
    with rasterio.open(_args.noaa) as noaa, rasterio.open(_args.nrcan) as nrcan:
        height, width = noaa.height, noaa.width
        core = Window(col, row, min(BLOCK, width - col), min(BLOCK, height - row))
        # Pixel size on the ground at this block's latitude, for measuring the ramp.
        lat = noaa.xy(row + core.height // 2, col)[1]
        dy = abs(noaa.transform.e) * 111320
        dx = noaa.transform.a * 111320 * math.cos(math.radians(lat))
        pad_r, pad_c = math.ceil(_args.ramp / dy), math.ceil(_args.ramp / dx)
        r0, c0 = max(0, row - pad_r), max(0, col - pad_c)
        r1, c1 = min(height, row + core.height + pad_r), min(width, col + core.width + pad_c)
        outer = Window(c0, r0, c1 - c0, r1 - r0)
        a = noaa.read(1, window=outer, masked=True)
        n = nrcan.read(1, window=outer, masked=True)

    has_a = ~np.ma.getmaskarray(a)
    has_n = ~np.ma.getmaskarray(n)
    out = np.full(a.shape, NODATA, dtype=np.float32)
    out[has_a] = a.data[has_a]
    out[has_n] = n.data[has_n]
    both = has_a & has_n
    if both.any() and not has_n.all():
        # Metres from each cell with Canadian data to the nearest cell without.
        inside = ndimage.distance_transform_edt(has_n, sampling=(dy, dx))
        w = np.clip(inside / _args.ramp, 0, 1).astype(np.float32)
        out[both] = w[both] * n.data[both] + (1 - w[both]) * a.data[both]

    inner = (slice(row - r0, row - r0 + core.height), slice(col - c0, col - c0 + core.width))
    return core, out[inner]


def _init(args: argparse.Namespace) -> None:
    global _args
    _args = args


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("noaa", help="NOAA's grid, warped to the output lattice")
    p.add_argument("nrcan", help="Canada's grid, warped to the same lattice")
    p.add_argument("output", help="GeoTIFF to write")
    p.add_argument("--ramp", type=float, default=4000, help="metres over which the two are blended")
    args = p.parse_args()

    with rasterio.open(args.noaa) as noaa, rasterio.open(args.nrcan) as nrcan:
        if (noaa.width, noaa.height, noaa.transform) != (nrcan.width, nrcan.height, nrcan.transform):
            raise SystemExit("the two grids must be on the same lattice")
        profile = noaa.profile
        height, width = noaa.height, noaa.width
    profile.update(
        driver="GTiff", dtype="float32", nodata=NODATA, count=1,
        tiled=True, blockxsize=512, blockysize=512, compress="deflate", predictor=3, bigtiff="if_safer",
    )

    jobs = [(r, c) for r in range(0, height, BLOCK) for c in range(0, width, BLOCK)]
    with rasterio.open(args.output, "w", **profile) as dst, mp.Pool(initializer=_init, initargs=(args,)) as pool:
        for window, data in pool.imap_unordered(_blend, jobs):
            dst.write(data, 1, window=window)
    print(f"{args.output}: {len(jobs)} blocks")


if __name__ == "__main__":
    main()
