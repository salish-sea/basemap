# /// script
# requires-python = ">=3.12"
# dependencies = ["rasterio>=1.4", "numpy>=2", "scipy>=1.14", "shapely>=2.1"]
# ///
"""Checks of the water mask (decisions/028).

    uv run scripts/check_mask.py selftest           the PNG writer, read back by GDAL and by hand
    uv run scripts/check_mask.py passes MASK.png    narrow passes: are they open water?

`passes` reads the JSON beside the mask for where the grid lies, and for each pass reports the
narrowest the water gets within about 2 km of it, in cells, and whether the water on either side
is the same piece of water.
"""

import json
import os
import struct
import sys
import zlib

import numpy as np
import rasterio
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from regions import png_1bit  # noqa: E402

# Name, latitude and longitude.
PASSES = [
    ("Dodd Narrows", 49.137, -123.818),
    ("Pole Pass (as asked)", 48.618, -122.975),
    ("Pole Pass (GNIS)", 48.602, -122.991),
    ("Active Pass", 48.868, -123.305),
    ("Porlier Pass", 49.014, -123.590),
    ("Deception Pass", 48.406, -122.643),
    ("Sansum Narrows", 48.78, -123.55),
    ("Tacoma Narrows", 47.27, -122.55),
]


def decode(png):
    """Reads back a PNG of the kind png_1bit writes, without any library."""
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    at, idat, header = 8, b"", None
    while at < len(png):
        n, kind = struct.unpack(">I4s", png[at:at + 8])
        data = png[at + 8:at + 8 + n]
        assert zlib.crc32(kind + data) == struct.unpack(">I", png[at + 8 + n:at + 12 + n])[0]
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", data)
        elif kind == b"IDAT":
            idat += data
        at += 12 + n
    cols, rows, depth, colour, _, _, interlace = header
    assert (depth, colour, interlace) == (1, 0, 0)
    stride = (cols + 7) // 8
    raw = np.frombuffer(zlib.decompress(idat), np.uint8).reshape(rows, stride + 1)
    assert not raw[:, 0].any()  # filter type 0 on every row
    return np.unpackbits(raw[:, 1:], axis=1)[:, :cols].astype(bool)


def selftest():
    rng = np.random.default_rng(1)
    # Widths that are and aren't a multiple of eight, and one a single cell wide.
    for rows, cols in ((1, 1), (3, 8), (5, 13), (64, 70), (200, 1001)):
        bits = rng.random((rows, cols)) < 0.5
        png = png_1bit(bits)
        assert (decode(png) == bits).all(), (rows, cols)
        path = f"{os.environ.get('TMPDIR', '/tmp')}/check_mask_{rows}x{cols}.png"
        open(path, "wb").write(png)
        with rasterio.open(path) as d:
            assert d.driver == "PNG" and (d.height, d.width) == (rows, cols)
            assert (d.read(1) == bits).all(), f"GDAL reads {rows}x{cols} differently"
        os.remove(path)
        os.remove(path + ".aux.xml") if os.path.exists(path + ".aux.xml") else None
    print("png writer: ok")


R = 30  # the window around a pass, in cells: about 2.8 km each way
NEAR = 10  # how far from the given point the narrowest part is looked for
EIGHT, FOUR = np.ones((3, 3)), ndimage.generate_binary_structure(2, 1)


def perimeter(n):
    """The cells on the edge of an n-by-n window, in order around it."""
    return ([(0, j) for j in range(n)] + [(i, n - 1) for i in range(1, n)]
            + [(n - 1, j) for j in range(n - 2, -1, -1)] + [(i, 0) for i in range(n - 2, 0, -1)])


def sides(win, structure):
    """The pairs of places on the window's edge that the water joins inside it: each place a run
    of at least three water cells along the edge, and the two at least ten cells apart along it."""
    lab, _ = ndimage.label(win, structure=structure)
    ring = perimeter(win.shape[0])
    runs, run = [], []
    for k, cell in enumerate(ring + ring[:1]):
        if win[cell] and k < len(ring):
            run.append(cell)
        elif run:
            if len(run) >= 3:
                runs.append(run)
            run = []
    pairs = []
    for i, x in enumerate(runs):
        for y in runs[i + 1:]:
            gap = abs(ring.index(x[0]) - ring.index(y[0]))
            if min(gap, len(ring) - gap) >= 10 and lab[x[0]] == lab[y[0]]:
                pairs.append((x, y))
    return pairs


def joined(win, structure, pair):
    lab, _ = ndimage.label(win, structure=structure)
    return bool({lab[c] for c in pair[0]} & {lab[c] for c in pair[1]} - {0})  # label 0 is no water


def passes(path):
    grid = json.load(open(os.path.splitext(path)[0] + ".json"))
    W, S, E, N = grid["bbox"]
    dx, dy = grid["cell"]
    with rasterio.open(path) as d:
        water = d.read(1) == grid["water"]
    assert water.shape == (grid["height"], grid["width"])
    n = 2 * R + 1
    print(f"{'pass':16} {'closed by a dam of radius':>26} {'joined 8-way, 4-way':>20}  {'cells across':>12}")
    for name, lat, lon in PASSES:
        r, c = int((N - lat) / dy), int((lon - W) / dx)
        wide = water[r - R - 12:r + R + 13, c - R - 12:c + R + 13]  # a margin, so the distances at the edge are true
        depth = ndimage.distance_transform_edt(wide)[12:12 + n, 12:12 + n]  # in cells, from the nearest land
        win = wide[12:12 + n, 12:12 + n]
        # The throat: the smallest disc of land which, set down within NEAR cells of the given
        # point, leaves some pair of places on the window's edge that the water joined no longer
        # joined. If a small disc can do that, the water goes through the pass, and the pass is
        # as narrow as the disc is wide.
        best = None  # (radius, centre, the pair it cuts)
        pairs = sides(win, EIGHT)
        yy, xx = np.ogrid[-R:R + 1, -R:R + 1]
        for rho in range(0, 8):
            for i, j in zip(*np.nonzero(win)):
                if (i - R) ** 2 + (j - R) ** 2 > NEAR ** 2:
                    continue
                dammed = win & ~((yy - (i - R)) ** 2 + (xx - (j - R)) ** 2 <= rho * rho)
                cut = next((p for p in pairs if not joined(dammed, EIGHT, p)), None)
                if cut:
                    best = (rho, (i, j), cut)
                    break
            if best:
                break
        if not best:
            print(f"{name:16} {'none up to 7':>26}  (no narrow throat within {NEAR} cells of the point)")
            continue
        rho, _, pair = best
        eight = joined(win, EIGHT, pair)
        four = joined(win, FOUR, pair)
        # The widest the pass can be kept while the two sides stay joined, keeping only cells at
        # least k from the land (eight-way, as above): a channel of that kind is 2k - 1 to 2k across.
        across = 0
        for k in range(1, 40):
            if joined(depth >= k, EIGHT, pair):
                across = k
            else:
                break
        print(f"{name:16} {rho:>26} {str(eight) + ', ' + str(four):>20}  {2 * across - 1 if across else 0}–{2 * across if across else 0}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["selftest"]:
        selftest()
    elif sys.argv[1:2] == ["passes"] and len(sys.argv) == 3:
        passes(sys.argv[2])
    else:
        sys.exit(__doc__)
