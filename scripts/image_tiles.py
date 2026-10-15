# /// script
# requires-python = ">=3.12"
# dependencies = ["rasterio>=1.4", "numpy>=2", "mercantile>=1.2"]
# ///
"""List the image tiles to draw (decisions/014), one `z x y` a line, in 256-pixel tiles.

Things that stitch tiles into a picture, rather than draw a map, need them at three
ranges of zoom:

- zooms 0 to 5 over the zoomed-out map's whole area, or the region's if it has none;
- zooms 6 to 10 over the region and a margin around it, because a picture framed on a
  sighting near the region's edge reaches past it; MARGIN tiles is half of SalishSea.io's
  profile picture, 720 pixels wide, and a tile more;
- zooms 11 to MAXZOOM only in the close-up area, and there only along the shore: every tile
  in which the depth grid goes both below and above 0 m, and the ring of tiles around those.
  Close-ups are for places on the shore, such as seal haul-outs; drawn everywhere, the
  Salish Sea alone would take 207,000 tiles, most of them inland or open water.
"""

import argparse
import sys
import warnings

import mercantile
import numpy as np
import rasterio
from affine import Affine
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT

MARGIN = 3
CLOSE_MINZOOM = 11
# The depth grid is read at this many cells across a close-up tile, each the lowest or the
# highest point under it, so a narrow channel or a rock isn't averaged away.
CELLS = 4


def bbox(text: str) -> tuple[float, float, float, float]:
    west, south, east, north = (float(v) for v in text.split(","))
    return west, south, east, north


def tile_range(box: tuple[float, float, float, float], z: int) -> tuple[int, int, int, int]:
    """The first and last column and row of the tiles that cover `box` at zoom `z`."""
    west, south, east, north = box
    first = mercantile.tile(west, north, z)
    last = mercantile.tile(east - 1e-9, south + 1e-9, z)
    return first.x, first.y, last.x, last.y


def ring(tiles: set[tuple[int, int]]) -> set[tuple[int, int]]:
    """The tiles and every tile that touches one of them."""
    return {(x + dx, y + dy) for x, y in tiles for dx in (-1, 0, 1) for dy in (-1, 0, 1)}


def shore_tiles(dem: str, box: tuple[float, float, float, float], z: int) -> set[tuple[int, int]]:
    """The tiles at zoom `z` within `box` in which the depth grid goes both below and above sea level."""
    x0, y0, x1, y1 = tile_range(box, z)
    left, _, _, top = mercantile.xy_bounds(x0, y0, z)
    size = mercantile.xy_bounds(x0, y0, z).right - left
    columns, rows = (x1 - x0 + 1) * CELLS, (y1 - y0 + 1) * CELLS
    def read(resampling: Resampling) -> np.ndarray:
        with rasterio.open(dem) as src, WarpedVRT(
            src, crs="EPSG:3857", transform=Affine(size / CELLS, 0, left, 0, -size / CELLS, top),
            width=columns, height=rows, resampling=resampling,
        ) as vrt:
            # Off the grid is neither sea nor land: nothing there to say which.
            grid = vrt.read(1, masked=True).filled(np.nan)
        return grid.reshape(rows // CELLS, CELLS, columns // CELLS, CELLS)

    # A tile wholly off the grid has no lowest or highest point, which numpy warns about.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        lowest = np.nanmin(read(Resampling.min), axis=(1, 3))
        highest = np.nanmax(read(Resampling.max), axis=(1, 3))
    return {(x0 + int(c), y0 + int(r)) for r, c in zip(*np.nonzero((lowest < 0) & (highest > 0)))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dem", help="the region's depth and height grid")
    parser.add_argument("out", help="the list to write")
    parser.add_argument("--bbox", type=bbox, required=True, help="the region: west,south,east,north")
    parser.add_argument("--overview", type=bbox, help="the zoomed-out map's area, if the region has one")
    parser.add_argument("--close", type=bbox, required=True, help="where close-ups are drawn")
    parser.add_argument("--maxzoom", type=int, default=15)
    args = parser.parse_args()

    outer = args.overview or args.bbox
    tiles: list[tuple[int, int, int]] = []
    for z in range(0, 11):
        ox0, oy0, ox1, oy1 = tile_range(outer, z)
        x0, y0, x1, y1 = tile_range(args.bbox, z)
        if z > 5:
            x0, y0, x1, y1 = max(x0 - MARGIN, ox0), max(y0 - MARGIN, oy0), min(x1 + MARGIN, ox1), min(y1 + MARGIN, oy1)
        else:
            x0, y0, x1, y1 = ox0, oy0, ox1, oy1
        tiles += [(z, x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]

    w, s, e, n = args.close
    close = (max(w, args.bbox[0]), max(s, args.bbox[1]), min(e, args.bbox[2]), min(n, args.bbox[3]))
    if close[0] < close[2] and close[1] < close[3]:
        level = ring(shore_tiles(args.dem, close, args.maxzoom))
        for z in range(args.maxzoom, CLOSE_MINZOOM - 1, -1):
            if z < args.maxzoom:
                level = ring({(x // 2, y // 2) for x, y in level})
            tiles += [(z, x, y) for x, y in sorted(level)]

    with open(args.out, "w") as f:
        f.writelines(f"{z} {x} {y}\n" for z, x, y in tiles)
    counts = {}
    for z, _, _ in tiles:
        counts[z] = counts.get(z, 0) + 1
    print(f"{len(tiles)} image tiles: " + ", ".join(f"z{z} {c}" for z, c in counts.items()), file=sys.stderr)


if __name__ == "__main__":
    main()
