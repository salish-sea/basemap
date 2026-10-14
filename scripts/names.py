# /// script
# requires-python = ">=3.12"
# dependencies = ["rasterio>=1.4", "numpy>=2", "scipy>=1.14", "pyproj>=3.7"]
# ///
"""Choose the marine names to label, and when and how each is drawn.

Reads the names of bays, straits, channels, passages and points from the USGS's
Geographic Names Information System (GNIS) for the US side and from the Canadian
Geographical Names Database (CGNDB) for the Canadian side, and writes them as GeoJSON
points, one per line, for tippecanoe (decisions/006).

Both sources give each name a single point, not the outline of the water it names. The
depth grid is used to judge the rest:

- A water body's name is moved from its point toward the middle of the water, up to
  3 km for a strait or channel and 300 m for a bay or cove. Its label is turned to run
  the way the water runs furthest, so a strait is written along its length, and it
  appears from the zoom at which it fits inside the water there, but no earlier than
  the generic part of the name allows (a strait before a channel, a channel before a
  cove).
- A point of land is kept only if it is on the sea, and is given an earlier zoom the
  more open water lies off it, so that headlands on the big straits appear before
  points inside coves.

Names that both countries record, such as Haro Strait, are kept once.
"""

import argparse
import csv
import json
import math
import re
import sys

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from scipy import ndimage, signal

# Kinds of feature kept from each source. GNIS files straits, sounds, inlets and
# passages as bays; CGNDB groups them by its concise codes.
GNIS_WATER = {"Bay", "Channel", "Gut"}
GNIS_POINT = {"Cape"}
CGN_WATER = {"BAY", "CHAN"}
CGN_POINT = {"CAPE"}
# CGNDB lists peninsulas under capes; they are land, not points on the water.
CGN_POINT_EXCLUDE = {"Peninsula"}

# The grid that distances are measured on, in Web Mercator metres: the units of the
# map's own pixels, so that a label's size in pixels converts straight into it.
CELL = 100.0
EARTH = 40075016.68557849
TILE = 512

# How the labels are drawn in the style (style/style.ts): roughly how wide a character
# is, and the letter spacing, both as a share of the text size.
CHAR_WIDTH = 0.55
LETTER_SPACING = 0.08


def water_name_size(zoom):
    """A water body's name size in pixels at the zoom it first appears, as `waterNameSize` in style/style.ts."""
    return 14 if zoom <= 8 else 13 if zoom <= 10 else 12


# How far a label may reach past the open water it names, as a share of that water's
# half-width. Above 1, a label may cover a little of the shore, as on Esri's map.
OVERHANG = 1.4

# Angles tried for a water body's label, in degrees anticlockwise from east, and the
# share of the longest run a more level angle needs to be chosen instead.
ANGLES = sorted(range(-85, 90, 5), key=abs)
LEVEL_SHARE = 0.8
# A label's line must stay in water at least this share as wide as at its point, and
# is followed no further than MAX_RUN metres each way.
WIDTH_KEPT = 0.4
MAX_RUN = 60000.0

# The earliest zoom for a water body's name, by the generic part of the name and by
# the scale CGNDB says a Canadian name is relevant at. About 1:250,000 is zoom 9 here.
GENERIC_ZOOMS = [
    (6, {"strait", "sound", "inlet", "sea", "gulf"}),
    (9, {"bay", "harbor", "harbour", "port"}),
    (10, {"passage", "pass", "channel", "arm", "basin", "narrows", "reach", "canal"}),
]
GENERIC_LAST = 11
RELEVANCE_ZOOMS = [(1000000, 6), (250000, 9), (0, 11)]
FRENCH_GENERICS = {"Détroit", "Mer", "Baie", "Chenal", "Passage", "Golfe", "Anse", "Pointe", "Cap", "Île", "Îles"}

# A name's point may sit on the shore or just inland of it in a 30 m grid.
COASTAL = 300.0
# How far, in metres, a water body's label may move from its point toward open water:
# further for the long, narrow kinds, whose points are often near one shore.
CLIMB = 300.0
CLIMB_LINEAR = 3000.0
LINEAR_GENERICS = {"strait", "sound", "inlet", "channel", "passage", "pass", "narrows", "reach"}

WATER_ZOOMS = (6, 14)
# How far apart, in metres on the ground, the two countries' points for one feature
# may be. Their points for the Strait of Juan de Fuca are 90 km apart.
SAME_WATER = 100000
SAME_POINT = 3000
# Points of land: the share of open water within each radius, in metres, that brings
# the point in at each zoom. Points meeting none of these appear at the last zoom.
POINT_ZOOMS = [(10, 8000, 0.78), (11, 3000, 0.7), (12, 1000, 0.55)]
POINT_LAST = 13


def log(*a):
    print(*a, file=sys.stderr)


def read_gnis(paths, bbox):
    west, south, east, north = bbox
    for path in paths:
        with open(path, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f, delimiter="|"):
                kind = "water" if row["feature_class"] in GNIS_WATER else "point" if row["feature_class"] in GNIS_POINT else None
                if kind is None:
                    continue
                lat, lon = float(row["prim_lat_dec"] or 0), float(row["prim_long_dec"] or 0)
                if west <= lon <= east and south <= lat <= north:
                    yield {"name": row["feature_name"], "kind": kind, "lon": lon, "lat": lat, "source": "gnis"}


def read_cgn(path, bbox):
    west, south, east, north = bbox
    # One row per name, and a feature can have an official name in each language, as
    # Juan de Fuca Strait has Détroit de Juan de Fuca. Keep one name per feature,
    # preferring one that isn't a French form.
    features = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            code = row["Concise Code"]
            kind = "water" if code in CGN_WATER else "point" if code in CGN_POINT and row["Generic Term"] not in CGN_POINT_EXCLUDE else None
            if kind is None:
                continue
            lat, lon = float(row["Latitude"]), float(row["Longitude"])
            if not (west <= lon <= east and south <= lat <= north):
                continue
            fid = row["Toponymic Feature ID"]
            name = row["Geographical Name"]
            french = row["ISO Language Code"] == "fra" or name.split(" ")[0] in FRENCH_GENERICS
            prev = features.get(fid)
            if prev is None or (prev[1] and not french):
                relevance = int(row["Relevance at Scale"] or 0)
                features[fid] = ({"name": name, "kind": kind, "lon": lon, "lat": lat, "source": "cgndb", "relevance": relevance}, french)
    for name, _ in features.values():
        yield name


def generic(name):
    """The generic part of a name: `strait` in both Haro Strait and Strait of Georgia."""
    words = name.lower().split()
    return words[0] if len(words) > 2 and words[1] == "of" else words[-1]


def earliest_zoom(n):
    """The earliest zoom a water body's name may appear at, whatever room it has.

    A name's point says nothing of how big the feature is: Middle Channel's point lies
    out in the open Strait of Juan de Fuca. So the generic part of the name sets a
    floor (a strait comes before a channel, a channel before a cove), and so, for
    Canadian names, does the map scale CGNDB says the name is relevant at."""
    zoom = next((z for z, terms in GENERIC_ZOOMS if generic(n["name"]) in terms), GENERIC_LAST)
    relevance = n.get("relevance")
    if relevance:
        zoom = max(zoom, next(z for scale, z in RELEVANCE_ZOOMS if relevance >= scale))
    return zoom


def same_name_key(name):
    """`Strait of Juan de Fuca` (US) and `Juan de Fuca Strait` (Canada) are one strait."""
    n = name.lower().strip()
    m = re.match(r"^(strait|sound|bay|channel|passage|pass|inlet|harbor|harbour) of (.+)$", n)
    if m:
        n = f"{m.group(2)} {m.group(1)}"
    return n.replace("harbour", "harbor")


def distance(a, b):
    """Metres along the ground between two names' points."""
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b["lon"] - a["lon"]) / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def disk(radius_cells):
    r = int(math.ceil(radius_cells))
    y, x = np.ogrid[-r:r + 1, -r:r + 1]
    return (x * x + y * y <= radius_cells * radius_cells).astype(np.float32)


def metres_per_pixel(zoom):
    return EARTH / (TILE * 2 ** zoom)


def fit_zoom(half_extent_px, room_m):
    """The zoom at which `half_extent_px` pixels cover `room_m` metres, times the overhang."""
    if room_m <= 0:
        return math.inf
    return math.log2(EARTH * half_extent_px / (TILE * OVERHANG * room_m))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("dem", help="elevation grid in metres, negative below sea level")
    p.add_argument("output", help="GeoJSON text sequence to write")
    p.add_argument("--gnis", action="append", default=[], help="a GNIS domestic names file (pipe-separated); may repeat")
    p.add_argument("--cgn", required=True, help="a CGNDB names file (CSV)")
    p.add_argument("--bbox", required=True, help="west,south,east,north in degrees")
    args = p.parse_args()
    bbox = tuple(map(float, args.bbox.split(",")))

    to_merc = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    to_geo = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
    x0, y0 = to_merc.transform(bbox[0], bbox[1])
    x1, y1 = to_merc.transform(bbox[2], bbox[3])
    width, height = int(math.ceil((x1 - x0) / CELL)), int(math.ceil((y1 - y0) / CELL))
    transform = rasterio.transform.from_origin(x0, y1, CELL, CELL)

    with rasterio.open(args.dem) as src, WarpedVRT(
        src, crs="EPSG:3857", transform=transform, width=width, height=height, resampling=Resampling.average,
    ) as vrt:
        elev = vrt.read(1, masked=True)
    # Where the grid has no data, as past the edge of the area, count it as sea, so that
    # a strait running off the edge is not taken to end there.
    sea = np.ma.filled(elev < 0, True)
    room = ndimage.distance_transform_edt(sea) * CELL  # from each sea cell to the nearest land
    inland = ndimage.distance_transform_edt(~sea) * CELL  # from each land cell to the nearest sea
    openness = {r: signal.fftconvolve(sea.astype(np.float32), disk(r / CELL) / disk(r / CELL).sum(), mode="same")
                for _, r, _ in POINT_ZOOMS}

    names = list(read_gnis(args.gnis, bbox)) + list(read_cgn(args.cgn, bbox))
    log(f"{len(names)} candidate names")

    def cell(lon, lat):
        x, y = to_merc.transform(lon, lat)
        return int((y1 - y) // CELL), int((x - x0) // CELL)

    kept = []
    for n in names:
        row, col = cell(n["lon"], n["lat"])
        if not (0 <= row < height and 0 <= col < width):
            continue
        if not sea[row, col] and inland[row, col] > COASTAL:
            continue  # a lake's bay, or a point inland
        if n["kind"] == "water":
            n.update(place_water(n, row, col, room, transform, to_geo))
            # Among names that a floor holds back to the same zoom, the one with most
            # room is placed first.
            n["rank"] = max(n["zoom"], earliest_zoom(n)) + min(n["zoom"], 20) / 100
            n["zoom"] = max(n["zoom"], earliest_zoom(n))
        else:
            n.update(place_point(row, col, openness))
        if n["zoom"] <= WATER_ZOOMS[1]:
            kept.append(n)

    # One label per name where both countries record a feature, as both record Haro
    # Strait: keep the point with the most open water around it. Within one source, two
    # names alike are two features, such as the several Echo Bays.
    best = {}
    for n in kept:
        key = (n["kind"], same_name_key(n["name"]))
        for other in best.get(key, []):
            near = SAME_WATER if n["kind"] == "water" else SAME_POINT
            if other["source"] != n["source"] and distance(n, other) < near:
                if n["room"] > other["room"]:
                    best[key].remove(other)
                    best[key].append(n)
                break
        else:
            best.setdefault(key, []).append(n)

    count = 0
    with open(args.output, "w") as out:
        for group in best.values():
            for n in group:
                minzoom = max(WATER_ZOOMS[0], math.ceil(n["zoom"] - 1e-9))
                props = {"name": n["name"], "kind": n["kind"], "minzoom": minzoom, "rank": round(n.get("rank", n["zoom"]), 2)}
                if n["kind"] == "water":
                    props["angle"] = n["angle"]
                feature = {
                    "type": "Feature",
                    # tippecanoe leaves the name out of tiles below its zoom.
                    "tippecanoe": {"minzoom": min(minzoom, 12)},
                    "properties": props,
                    "geometry": {"type": "Point", "coordinates": [round(n["lon"], 6), round(n["lat"], 6)]},
                }
                out.write(json.dumps(feature, ensure_ascii=False) + "\n")
                count += 1
    log(f"{count} names written")


def place_water(n, row, col, room, transform, to_geo):
    # Move the label from its point toward the middle of the water, uphill on the
    # distance from shore, but only so far: a strait's point is often near one shore,
    # while a cove's must not climb out of the cove into the water beyond it.
    reach = (CLIMB_LINEAR if generic(n["name"]) in LINEAR_GENERICS else CLIMB) / CELL
    start = (row, col)
    while True:
        r0, c0 = max(0, row - 2), max(0, col - 2)
        window = room[r0:row + 3, c0:col + 3]
        dr, dc = np.unravel_index(np.argmax(window), window.shape)
        if window[dr, dc] <= room[row, col] or math.dist(start, (r0 + dr, c0 + dc)) > reach:
            break
        row, col = r0 + dr, c0 + dc
    here = float(room[row, col])
    if here <= 0:
        return {"zoom": math.inf, "room": 0.0, "angle": 0}
    x, y = rasterio.transform.xy(transform, row, col)
    lon, lat = to_geo.transform(x, y)

    # Try the label at each angle, as a straight line centred on its point, and see how
    # far the line runs each way through water still at least a share as wide as here
    # (WIDTH_KEPT). In a strait the longest run is along the strait.
    across = here * WIDTH_KEPT
    steps = np.arange(1, int(MAX_RUN // CELL))
    runs = {}
    for angle in ANGLES:
        theta = math.radians(angle)
        run = math.inf
        for sign in (1, -1):
            rr = np.round(row - sign * steps * math.sin(theta)).astype(int)
            cc = np.round(col + sign * steps * math.cos(theta)).astype(int)
            inside = (rr >= 0) & (rr < room.shape[0]) & (cc >= 0) & (cc < room.shape[1])
            ok = np.zeros(len(steps), bool)
            ok[inside] = room[rr[inside], cc[inside]] >= across
            # A run that leaves the grid is taken to go on past its edge.
            ok[~inside] = True
            blocked = np.flatnonzero(~ok)
            run = min(run, (blocked[0] if len(blocked) else len(steps)) * CELL)
        runs[angle] = run
    # The label runs the way the water runs furthest, or as near level as gets most of
    # that length. ANGLES runs outward from level.
    longest = max(runs.values())
    angle = next(a for a in ANGLES if runs[a] >= LEVEL_SHARE * longest)
    # The first zoom at which the label, at the size it is drawn at that zoom, fits.
    # Earlier names are drawn bigger, so a fit is checked zoom by zoom.
    zoom = math.inf
    for z in range(WATER_ZOOMS[0], WATER_ZOOMS[1] + 1):
        size = water_name_size(z)
        half_width_px = len(n["name"]) * (CHAR_WIDTH + LETTER_SPACING) * size / 2
        fits = max(fit_zoom(half_width_px, runs[angle]), fit_zoom(size * 0.6, here))
        if fits <= z:
            # Not before this zoom: at the one before, the label is drawn bigger.
            zoom = max(fits, z - 0.999)
            break
    # MapLibre turns text clockwise, and the angles here run anticlockwise from east.
    return {"zoom": zoom, "room": here, "angle": -angle, "lon": lon, "lat": lat}


def place_point(row, col, openness):
    zoom = POINT_LAST
    for z, radius, share in POINT_ZOOMS:
        if openness[radius][row, col] >= share:
            zoom = z
            break
    # Within a zoom, the more open water within the widest radius, the earlier a point
    # is placed when labels compete for room.
    widest = float(openness[POINT_ZOOMS[0][1]][row, col])
    return {"zoom": zoom, "rank": zoom + 0.99 * (1 - widest), "room": widest}


if __name__ == "__main__":
    main()
