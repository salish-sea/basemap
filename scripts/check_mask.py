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
import tempfile
import zlib

import numpy as np
import rasterio
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from regions import DX, DY, land_cells, png_1bit, sea_of  # noqa: E402
from rasterio.features import rasterize  # noqa: E402
from rasterio.transform import from_bounds  # noqa: E402
from shapely.geometry import LineString, Point, box  # noqa: E402

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
    with tempfile.TemporaryDirectory() as tmp:
        # Widths that are and aren't a multiple of eight, and one a single cell wide.
        for rows, cols in ((1, 1), (3, 8), (5, 13), (64, 70), (200, 1001)):
            bits = rng.random((rows, cols)) < 0.5
            png = png_1bit(bits)
            assert (decode(png) == bits).all(), (rows, cols)
            path = os.path.join(tmp, f"{rows}x{cols}.png")
            open(path, "wb").write(png)
            with rasterio.open(path) as d:
                assert d.driver == "PNG" and (d.height, d.width) == (rows, cols)
                assert (d.read(1) == bits).all(), f"GDAL reads {rows}x{cols} differently"
    print("png writer: ok")
    spits()


def spits():
    """land_cells on made-up land at Port Angeles, each case beside one the centres alone get
    wrong or that a looser rule would: a spit at Ediz Hook's angle, a spit with a lagoon behind
    it and a narrow mouth, and a jetty that is a polygon on its own must stop the water from
    crossing them; an islet must gain no cell; two thin islands must keep the pass between them
    open; and a bay whose mouth a thin point of the same shore nearly closes, as at Malibu
    Rapids, must still reach the sea."""
    W, S, E, N = -123.50, 48.10, -123.30, 48.17
    cols, rows = round((E - W) / DX), round((N - S) / DY)
    T = from_bounds(W, S, E, N, cols, rows)
    inv = ~T
    def cell(lon, lat):
        c, r = inv * (lon, lat)
        return int(r), int(c)
    thin = lambda *points, half=0.00045: LineString(points).buffer(half, cap_style="flat")  # noqa: E731

    shore = box(W, S, E, 48.115)
    # Out from the shore to the east-north-east, as Ediz Hook runs, about 100 m wide.
    ediz = shore.union(thin((-123.47, 48.11), (-123.47, 48.135), (-123.405, 48.142)))
    islet = Point(-123.43, 48.16).buffer(0.0003)  # about 40 m across
    # Two islands about 65 m wide, at a shallow angle, with a pass about 155 m wide between them.
    south_island = thin((-123.495, 48.1500), (-123.465, 48.1515), half=0.0003)
    north_island = thin((-123.495, 48.1520), (-123.465, 48.1535), half=0.0003)
    # A shore with a bay in it, open to the west, and a point from its north side about 60 m wide
    # that reaches to within 120 m of its south side.
    bay = box(-123.416, 48.1505, -123.385, 48.1645)
    mainland = box(-123.415, 48.146, -123.38, 48.17).difference(bay).union(box(-123.4113, 48.1516, -123.4107, 48.165))
    # A spit with a lagoon behind it, whose mouth, at the spit's tip, is about 110 m wide.
    lagoon_spit = thin((-123.37, 48.11), (-123.37, 48.125), (-123.33, 48.128))
    headland = box(-123.3285, S, -123.31, 48.135)
    # A jetty about 30 m wide, on its own.
    jetty = thin((-123.36, 48.160), (-123.34, 48.1612), half=0.00013)
    polygons = [ediz, islet, south_island, north_island, mainland, lagoon_spit, headland, jetty]

    water, locks = np.ones((rows, cols), bool), np.zeros((rows, cols), bool)
    centre = rasterize(((p, 1) for p in polygons), out_shape=(rows, cols), transform=T, dtype=np.uint8) == 1
    old = sea_of(water & ~centre, locks)
    sea = sea_of(water & ~land_cells(polygons, water, (rows, cols), T), locks)

    def crosses(mask, north, south, west, east):
        """Whether the water joins the two points inside the box, which leaves out a barrier's ends."""
        (r0, c0), (r1, c1) = cell(west, north), cell(east, south)
        lab, _ = ndimage.label(mask[r0:r1 + 1, c0:c1 + 1], structure=EIGHT)
        (ra, ca), (rb, cb) = cell((west + east) / 2, north), cell((west + east) / 2, south)
        return lab[ra - r0, ca - c0] > 0 and lab[ra - r0, ca - c0] == lab[rb - r0, cb - c0]
    for name, box_ in (("Ediz Hook", (48.150, 48.128, -123.465, -123.41)),
                       ("the lagoon's spit", (48.135, 48.118, -123.365, -123.335)),
                       ("the jetty", (48.163, 48.158, -123.358, -123.342))):
        assert crosses(old, *box_), f"the test's {name} should be leaky by the centres alone"
        assert not crosses(sea, *box_), f"water still crosses {name}"
    assert sea[cell(-123.35, 48.120)], "the lagoon was cut off from the sea"
    r, c = cell(-123.43, 48.16)
    assert (sea[r - 3:r + 4, c - 3:c + 4] == old[r - 3:r + 4, c - 3:c + 4]).all(), "the islet grew"
    # The pass: the cells whose centres lie between the two islands' middle lines.
    between = rasterize([(thin((-123.497, 48.1510), (-123.463, 48.1525), half=0.0006), 1)],
                        out_shape=(rows, cols), transform=T, dtype=np.uint8) == 1
    west_end, east_end = cell(-123.4965, 48.1510), cell(-123.4635, 48.1525)
    for mask, problem in ((old, "the test's pass should be open by the centres alone"), (sea, "the pass between the islands was shut")):
        lab, _ = ndimage.label(mask & between, structure=EIGHT)
        assert lab[west_end] > 0 and lab[west_end] == lab[east_end], problem
    assert old[cell(-123.395, 48.157)], "the test's bay should reach the sea by the centres alone"
    assert sea[cell(-123.395, 48.157)], "the bay was cut off from the sea"
    # Land that reaches beyond the grid, as when --bbox is smaller than the land, is passed over.
    beyond = thin((E + 0.01, 48.12), (E + 0.03, 48.13))
    assert (land_cells([beyond], water, (rows, cols), T) == False).all(), "land beyond the grid made cells land"  # noqa: E712
    print("thin land: ok")


R = 30  # the window around a pass, in cells: about 2.8 km each way
MIN_SIDE = 200  # cells: the least a piece of water at the window's edge may hold to be a side of a pass
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
        margin = R + 12  # the window and its margin must lie wholly inside the mask
        if not (margin <= r < water.shape[0] - margin and margin <= c < water.shape[1] - margin):
            print(f"{name:16} outside the mask")
            continue
        wide = water[r - R - 12:r + R + 13, c - R - 12:c + R + 13]  # a margin, so the distances at the edge are true
        depth = ndimage.distance_transform_edt(wide)[12:12 + n, 12:12 + n]  # in cells, from the nearest land
        win = wide[12:12 + n, 12:12 + n]
        # The water that touches the window's edge, in pieces. More than one means the water is not
        # joined inside the window: the pass may be shut here (or the window is split by land).
        lab, _ = ndimage.label(win, structure=EIGHT)
        edge = np.zeros_like(win)
        edge[0, :] = edge[-1, :] = edge[:, 0] = edge[:, -1] = True
        pieces = sorted((int((lab == v).sum()) for v in np.unique(lab[edge & win])), reverse=True)
        # A piece of a few cells is a bay or inlet the window cuts off, not a side of the pass.
        big = [p for p in pieces if p >= MIN_SIDE]
        if len(big) >= 2:
            print(f"{name:16} water in {len(big)} separate pieces: the pass may be shut here "
                  f"(sizes in cells: {', '.join(map(str, pieces))})")
            continue
        seen = f"pieces at the edge: {len(pieces)} ({', '.join(map(str, pieces))} cells)"
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
            print(f"{name:16} {'none up to 7':>26} {'open water':>20}  {'':>12}  {seen}")
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
        print(f"{name:16} {rho:>26} {str(eight) + ', ' + str(four):>20}  {str(2 * across - 1 if across else 0) + '–' + str(2 * across):>12}  {seen}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["selftest"]:
        selftest()
    elif sys.argv[1:2] == ["passes"] and len(sys.argv) == 3:
        passes(sys.argv[2])
    else:
        sys.exit(__doc__)
