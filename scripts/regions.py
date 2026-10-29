# /// script
# requires-python = ">=3.12"
# dependencies = ["rasterio>=1.4", "numpy>=2", "scipy>=1.14", "shapely>=2.1", "pmtiles>=3.4", "mapbox-vector-tile>=2.1"]
# ///
"""Divide the water into one region per water name the map labels (decisions/027).

    uv run scripts/regions.py DEM NAMES OUTLINES DRYING PROTOMAPS PLACES_OSM KNOWN OVERRIDES OUT.geojsons \\
        --bbox=W,S,E,N --report=REPORT.json

Reads the depth grid, the labelled names (scripts/names.py), the two gazetteers' outlines
(scripts/region_outlines.py), the ground that dries at low tide, OpenStreetMap's land from the
Protomaps archive, the OpenStreetMap place list (to tell repeated names apart), the names
sighting reports use (regions-known.tsv) and the hand-kept corrections (regions-overrides.json).
Writes one region per line, its `name` as a card would say it and `base` as the map labels it,
and a report of the names that are no region and the regions in pieces.

Everything is worked out on a grid of about 90 m in longitude and latitude, in steps:

1. Water: the depth grid below zero, and ground that dries, less OpenStreetMap's land.
2. Names: each labelled water name and place, less coves and bights reports don't name, a
   chart's navigation ranges and the hand-kept drops; with its outlines, if either source has
   one near the label.
3. Seeds: outlines, largest first so the smallest nested one wins; then each name with only a
   point takes the water its shore encloses, or, failing that, the water along its shore.
4. Growth: every other water cell joins the nearest seed, a ring at a time through the water.
   On the outer coast, open water far from any name's own is the coast's.
5. Skirt: each region reaches about 300 m onto the land beside it.
6. Polygons, smoothed together so neighbours still share their edges.
"""

import argparse
import collections
import gzip
import json
import math
import os
import re

import mapbox_vector_tile
import numpy as np
import rasterio
import shapely
from pmtiles.reader import MmapSource, Reader
from rasterio.enums import MergeAlg, Resampling
from rasterio.features import rasterize, shapes
from rasterio.transform import from_bounds, rowcol
from rasterio.windows import from_bounds as window_from_bounds
from scipy import ndimage
from shapely.geometry import Point, mapping, shape
from shapely.ops import unary_union

# The grid, in degrees: about 93 m each way at 48°N.
DX, DY = 0.00125, 0.000833
CELL_KM = 0.093
# How far a name with only a point is looked for around its label, by the zoom its label
# appears from; at least about 500 m, since a label sits up to 300 m off its shore.
RADIUS_KM = {6: 6, 7: 4, 8: 3, 9: 2, 10: 1.2, 11: 0.6, 12: 0.35, 13: 0.25}
MIN_RADIUS = 5
# The widths of mouth a bay is closed across, in cells, smallest first: up to about 3 km.
MOUTHS = (3, 5, 8, 12, 16)
# A piece of a region smaller than this, cut off from the rest, rejoins its neighbours.
MIN_PIECE = 25  # cells, about 0.2 km²
# How far a region reaches onto the land beside it.
SKIRT = 3  # cells, about 300 m
# A channel's kinds of name: water between shores, rather than a bay a shore encloses.
BETWEEN_SHORES = ("channel", "passage", "pass", "reach", "narrows", "narrow")


def norm(name):
    n = name.lower().replace("harbour", "harbor").replace("strait of juan de fuca", "juan de fuca strait")
    return re.sub(r"\s+", " ", n).strip()


def generic(name):
    words = name.lower().split()
    return words[-1] if words else ""


def km(a, b):
    x = math.radians(b[0] - a[0]) * math.cos(math.radians((a[1] + b[1]) / 2))
    return 6371 * math.hypot(x, math.radians(b[1] - a[1]))


def disc(r):
    y, x = np.ogrid[-r:r + 1, -r:r + 1]
    return (x * x + y * y) <= r * r


def enclosed_by(land, r):
    """Land and the water it encloses once its gaps up to 2r wide are closed: grow the land to
    close the mouths, fill what is then cut off from the edge, and shrink the land back."""
    grown = ndimage.binary_dilation(land, structure=disc(r), border_value=0)
    filled = ndimage.binary_fill_holes(grown)
    return ndimage.binary_erosion(filled, structure=disc(r), border_value=1) | land


def lines(path):
    """The features of a GeoJSON text sequence, with or without record separators."""
    for line in open(path):
        line = line.strip("\x1e \n")
        if line:
            yield json.loads(line)


def osm_land(protomaps, transform, shape_, bbox, zoom=11):
    """OpenStreetMap's land, from the Protomaps archive's `earth` layer at `zoom`, on the grid."""
    west_, south_, east_, north_ = bbox
    n = 2 ** zoom

    def tile_xy(lon, lat):
        return int((lon + 180) / 360 * n), int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)

    def lat_of(y):
        return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))

    earth = np.zeros(shape_, dtype=np.uint8)
    with open(protomaps, "rb") as fh:
        reader = Reader(MmapSource(fh))
        (x0, y0), (x1, y1) = tile_xy(west_, north_), tile_xy(east_, south_)
        for tx in range(x0, x1 + 1):
            for ty in range(y0, y1 + 1):
                data = reader.get(zoom, tx, ty)
                if not data:
                    continue
                if data[:2] == b"\x1f\x8b":
                    data = gzip.decompress(data)
                layer = mapbox_vector_tile.decode(data, default_options={"y_coord_down": True}).get("earth")
                if not layer:
                    continue
                ext = layer.get("extent", 4096)
                west, east = tx / n * 360 - 180, (tx + 1) / n * 360 - 180

                def to_lonlat(ring):
                    return [(west + (east - west) * px / ext, lat_of(ty + py / ext)) for px, py in ring]

                polygons = []
                for f in layer["features"]:
                    g = f["geometry"]
                    parts = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"] if g["type"] == "MultiPolygon" else []
                    polygons += [({"type": "Polygon", "coordinates": [to_lonlat(r) for r in p]}, 1) for p in parts]
                if polygons:
                    rasterize(polygons, out=earth, transform=transform, merge_alg=MergeAlg.replace)
    return earth == 1


def main():
    ap = argparse.ArgumentParser()
    for arg in ("dem", "names", "outlines", "drying", "protomaps", "places_osm", "known", "overrides", "out"):
        ap.add_argument(arg)
    ap.add_argument("--bbox", required=True)
    ap.add_argument("--report", required=True)
    a = ap.parse_args()
    W, S, E, N = map(float, a.bbox.split(","))
    cols, rows = round((E - W) / DX), round((N - S) / DY)
    T = from_bounds(W, S, E, N, cols, rows)
    known = {norm(r.split("\t")[0]): int(r.split("\t")[1]) for r in open(a.known).read().splitlines()[1:]}
    ov = json.load(open(a.overrides))

    # 1. Water.
    with rasterio.open(a.dem) as d:
        elev = d.read(1, window=window_from_bounds(W, S, E, N, d.transform), out_shape=(rows, cols), resampling=Resampling.average)
    water = (elev < 0) & (elev > -20000)
    del elev
    water |= rasterize(((f["geometry"], 1) for f in lines(a.drying)), out_shape=(rows, cols), transform=T,
                       dtype=np.uint8, all_touched=True) == 1
    water &= ~osm_land(a.protomaps, T, (rows, cols), (W, S, E, N))
    print(f"grid {rows} by {cols}, {int(water.sum())} cells of water")

    # 2. Names: one region per name and place, so two Rocky Bays are two regions.
    groups = []
    for f in lines(a.names):
        p = f["properties"]
        x, y = f["geometry"]["coordinates"]
        if p["kind"] != "water" or not (W <= x <= E and S <= y <= N):
            continue
        same = next((g for g in groups if g["key"] == norm(p["name"]) and km(g["points"][0], (x, y)) < 15), None)
        if same:
            same["points"].append((x, y))
            same["minzoom"] = min(same["minzoom"], p["minzoom"])
        else:
            groups.append({"name": p["name"], "key": norm(p["name"]), "points": [(x, y)], "minzoom": p["minzoom"], "also": []})

    def near(g, entry):
        return "near" not in entry or km(g["points"][0], entry["near"]) < 5

    kept = []
    for g in groups:
        if any(e["name"] == g["name"] and near(g, e) for e in ov["drop"]):
            continue
        if generic(g["name"]) in ("cove", "bight") and known.get(g["key"], 0) < 2:
            continue
        if generic(g["name"]) == "range":
            continue
        for e in ov["rename"]:
            if e["name"] == g["name"] and near(g, e):
                g["name"] = e["to"]
        kept.append(g)
    for e in ov["merge"]:
        into = next((g for g in kept if g["name"] == e["into"]), None)
        for g in [g for g in kept if g["name"] == e["name"]]:
            if into and km(g["points"][0], into["points"][0]) < 10:
                into["points"] += g["points"]
                into["minzoom"] = min(into["minzoom"], g["minzoom"])
                into["also"].append(g["key"])
                kept.remove(g)
    print(f"{len(groups)} labelled water names, {len(kept)} kept")
    groups = kept

    outlines = collections.defaultdict(list)
    for f in lines(a.outlines):
        outlines[norm(f["properties"]["name"])].append(shape(f["geometry"]).buffer(0))
    for g in groups:
        here = [o for k in [g["key"], *g["also"]] for o in outlines.get(k, []) if o.distance(Point(g["points"][0])) < 0.05]
        g["outline"] = unary_union(here) if here else None

    # 3. Seeds: outlines, largest first, so the smallest nested one wins.
    labels = np.zeros((rows, cols), dtype=np.int32)
    for i in sorted((i for i, g in enumerate(groups) if g["outline"]), key=lambda i: -groups[i]["outline"].area):
        burn = rasterize([(mapping(groups[i]["outline"]), 1)], out_shape=(rows, cols), transform=T, dtype=np.uint8)
        labels[(burn == 1) & water] = i + 1
    # A name with only a point takes the water its shore encloses; a channel, or a bay reports
    # name or the map labels early, that encloses nothing takes the water along its shore.
    shapeless = set()
    for i, g in sorted(((i, g) for i, g in enumerate(groups) if not g["outline"]), key=lambda ig: ig[1]["minzoom"]):
        rc = max(int(RADIUS_KM.get(int(g["minzoom"]), 0.25) / CELL_KM), MIN_RADIUS)
        claimed = False
        for (x, y) in g["points"]:
            row, col = rowcol(T, x, y)
            if not (0 <= row < rows and 0 <= col < cols):
                continue
            # A label's zoom says little of a narrow bay's length, so look at least 3.7 km around it.
            pad = max(4 * rc, 40)
            r0, r1, c0, c1 = max(row - pad, 0), min(row + pad + 1, rows), max(col - pad, 0), min(col + pad + 1, cols)
            wat, sub = water[r0:r1, c0:c1], labels[r0:r1, c0:c1]
            rr, cc = row - r0, col - c0
            yy, xx = np.ogrid[0:wat.shape[0], 0:wat.shape[1]]
            dist2 = (yy - rr) ** 2 + (xx - cc) ** 2
            for mouth in sorted({*MOUTHS, max(rc // 2, 3), rc}):
                comp, n = ndimage.label(enclosed_by(~wat, mouth) & wat, structure=np.ones((3, 3)))
                if not n:
                    continue
                ys, xs = np.nonzero(comp)
                k = np.argmin((ys - rr) ** 2 + (xs - cc) ** 2)
                if (ys[k] - rr) ** 2 + (xs[k] - cc) ** 2 > (rc // 2 + 2) ** 2:
                    continue
                pick = comp == comp[ys[k], xs[k]]
                if pick.sum() > 0.4 * wat.size:
                    continue
                sub[pick] = i + 1
                claimed = True
                break
            if claimed:
                continue
            if generic(g["name"]) in BETWEEN_SHORES or known.get(g["key"], 0) >= 1 or g["minzoom"] <= 11:
                # The label's distance from the shore is the measure: the water near the label no
                # farther from land than the label, give or take a quarter.
                to_land = ndimage.distance_transform_edt(wat)
                d0 = to_land[rr, cc] if wat[rr, cc] else 1
                band = wat & (to_land <= 1.25 * d0 + 2) & (dist2 <= max(3 * rc // 2, 2 * d0) ** 2)
                comp, n = ndimage.label(band, structure=np.ones((3, 3)))
                if n:
                    ys, xs = np.nonzero(comp)
                    k = np.argmin((ys - rr) ** 2 + (xs - cc) ** 2)
                    sub[comp == comp[ys[k], xs[k]]] = i + 1
                    claimed = True
        if not claimed:
            shapeless.add(i)
    # Every label lies in its own region, where it is on water.
    for i, g in enumerate(groups):
        if i in shapeless:
            continue
        for (x, y) in g["points"]:
            row, col = rowcol(T, x, y)
            if 1 <= row < rows - 1 and 1 <= col < cols - 1:
                labels[row - 1:row + 2, col - 1:col + 2][water[row - 1:row + 2, col - 1:col + 2]] = i + 1

    # 4. Growth through the water, a ring at a time, so a cell joins the seed nearest it by water.
    def grow(within):
        steps = np.where(labels > 0, 0, -1).astype(np.int32)
        flat_l, flat_w, flat_s = labels.ravel(), within.ravel(), steps.ravel()
        frontier, step = np.flatnonzero(flat_l > 0), 0
        while frontier.size:
            step += 1
            src_all, dst_all = [], []
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
                c = frontier % cols + dc
                src = frontier[(c >= 0) & (c < cols)]
                dst = src + dr * cols + dc
                ok = (dst >= 0) & (dst < flat_l.size)
                src, dst = src[ok], dst[ok]
                ok = flat_w[dst] & (flat_l[dst] == 0)
                src_all.append(src[ok])
                dst_all.append(dst[ok])
            dst, first = np.unique(np.concatenate(dst_all), return_index=True)
            flat_l[dst] = flat_l[np.concatenate(src_all)[first]]
            flat_s[dst] = step
            frontier = dst
        return steps

    steps = grow(water)
    # A small piece cut off from its region rejoins whatever it touches; the piece holding the
    # label, or else the largest, stays.
    for v, sl in enumerate(ndimage.find_objects(labels), start=1):
        if sl is None or v > len(groups):
            continue
        comp, n = ndimage.label(labels[sl] == v, structure=np.ones((3, 3)))
        if n <= 1:
            continue
        sizes = ndimage.sum(np.ones_like(comp), comp, index=range(1, n + 1))
        keep = int(np.argmax(sizes)) + 1
        row, col = rowcol(T, *groups[v - 1]["points"][0])
        r, c = row - sl[0].start, col - sl[1].start
        if 0 <= r < comp.shape[0] and 0 <= c < comp.shape[1] and comp[r, c]:
            keep = comp[r, c]
        for k in range(1, n + 1):
            if k != keep and sizes[k - 1] < MIN_PIECE:
                labels[sl][comp == k] = 0
    steps = np.maximum(steps, grow(water))

    # On the outer coast, past the mouth of the Strait of Juan de Fuca, open water more than 1.5 km
    # from a name's own is the coast's. Sheltered water, as Grays Harbor's, is what closing the
    # land over gaps of about 5 km fills, worked out on a grid ten times coarser.
    lon = W + (np.arange(cols) + 0.5) * DX
    lat = (N - (np.arange(rows) + 0.5) * DY)[:, None]
    coarse = ndimage.zoom((~water).astype(np.uint8), 0.1, order=0).astype(bool)
    sheltered = np.kron(enclosed_by(coarse, 3) & ~coarse, np.ones((10, 10), dtype=bool))
    sheltered = np.pad(sheltered, ((0, max(rows - sheltered.shape[0], 0)), (0, max(cols - sheltered.shape[1], 0))))[:rows, :cols]
    outer = ((lon[None, :] < -124.55) | ((lat < 47.95) & (lon[None, :] < -123.8))) & ~sheltered
    far = water & (((steps * CELL_KM > 8) & (lon[None, :] < -124.4)) | ((steps * CELL_KM > 1.5) & outer))
    coasts = [("off the Central Coast", lat >= 50.9), ("off Vancouver Island", (lat >= 48.4) & (lat < 50.9)),
              ("off the Washington coast", (lat < 48.4) & (lat >= 46.25)), ("off Oregon", lat < 46.25)]
    for k, (_, where) in enumerate(coasts):
        labels[far & where] = len(groups) + 1 + k

    # 5. The skirt over the shore, grown only after the water is all taken.
    domain = water | ndimage.binary_dilation(water, structure=disc(SKIRT))
    grow(domain)

    # 6. Polygons, smoothed together.
    pieces = collections.defaultdict(list)
    for geom, v in shapes(labels, mask=(labels > 0) & domain, transform=T, connectivity=8):
        pieces[int(v)].append(shape(geom))
    order = sorted(pieces)
    regions = dict(zip(order, shapely.coverage_simplify(np.array([unary_union(pieces[v]) for v in order]), 0.0007)))

    # Repeated names, told apart as a card would say them.
    osm = json.load(open(a.places_osm))
    c = {k: i for i, k in enumerate(osm["columns"])}
    marks = [(r[c["name"]], r[c["lon"]], r[c["lat"]]) for r in osm["places"] if r[c["kind"]] in ("island", "town", "village", "city")]
    shared = collections.Counter(groups[v - 1]["name"] for v in order if v <= len(groups))
    area = dict(zip(*np.unique(labels, return_counts=True)))
    objs = ndimage.find_objects(labels)

    def qualified(v):
        g = groups[v - 1]
        at = g["points"][0]
        hand = next((e["as"] for e in ov["qualify"] if e["name"] == g["name"] and km(at, e["near"]) < 5), None)
        if hand:
            return hand
        mark = min(marks, key=lambda m: km(at, (m[1], m[2])))
        if km(at, (mark[1], mark[2])) <= 2:
            return f"{g['name']} ({mark[0]})"
        sl = tuple(slice(max(s.start - 2, 0), s.stop + 2) for s in objs[v - 1])
        sub = labels[sl]
        ring = ndimage.binary_dilation(sub == v, structure=np.ones((3, 3))) & (sub != v)
        nb = collections.Counter(sub[ring].tolist())
        bigger = [(n, u) for u, n in nb.items() if 0 < u <= len(groups) and area.get(u, 0) > area[v]]
        if bigger:
            water_name = groups[max(bigger)[1] - 1]["name"]
            if not any(w in water_name.lower() for w in ("creek", "river", "slough")):
                return f"{g['name']} ({water_name})"
        return f"{g['name']} ({mark[0]})"

    with open(a.out + ".new", "w") as out:
        for v in order:
            if v <= len(groups):
                g = groups[v - 1]
                name = qualified(v) if shared[g["name"]] > 1 else g["name"]
                props = {"name": name, "base": g["name"]}
            else:
                props = {"name": coasts[v - len(groups) - 1][0], "base": coasts[v - len(groups) - 1][0]}
            # A hue to draw it in, spread so that neighbours, numbered near each other, differ.
            props["hue"] = v * 137 % 360
            out.write(json.dumps({"type": "Feature", "properties": props, "geometry": mapping(regions[v])}) + "\n")
    os.replace(a.out + ".new", a.out)

    split = [groups[v - 1]["name"] for v in order if v <= len(groups)
             and sum(1 for p in getattr(regions[v], "geoms", [regions[v]]) if p.area * 111 * 111 * math.cos(math.radians(48)) >= 0.5) > 1]
    json.dump({"no_region": sorted([groups[i]["name"], *map(lambda x: round(x, 4), groups[i]["points"][0])] for i in shapeless),
               "in_pieces": sorted(split)}, open(a.report, "w"), indent=1, ensure_ascii=False)
    print(f"{len(order)} regions; {len(shapeless)} names with no region; {len(split)} regions in more than one piece")


if __name__ == "__main__":
    main()
