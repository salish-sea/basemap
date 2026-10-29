# /// script
# requires-python = ">=3.12"
# dependencies = ["shapely>=2"]
# ///
"""Fetch the named water outlines that the water regions start from (decisions/027).

Two sources outline named water: Canada's geographical names service (CGNDB), for many
Canadian names and for the straits both countries share, and NOAA's electronic charts' named
sea areas (S-57 SEAARE, through ENC Direct) for US waters. Neither divides the sea; their
outlines nest and leave gaps, which scripts/regions.py resolves.

    uv run scripts/region_outlines.py CACHEDIR OUT.geojsons --bbox=W,S,E,N

Downloads into CACHEDIR once (each CGNDB name's file, and each chart scale's page of areas),
then writes one outline per line: its name, source and, for the charts, scale. The charts cut
one area at each cell's edge, so pieces of one name at one scale that touch are merged. The
general scale is left out: its outlines are coarse and a tenth of them lie on land.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union

CGNDB = "https://geogratis.gc.ca/services/geoname/en"
CGNDB_CONCISE = ["BAY", "CHAN", "SEA", "SEAF", "MAR"]
CGNDB_ID = re.compile(r"^[A-Z0-9]{4,8}$")
ENC = "https://encdirect.noaa.gov/arcgis/rest/services/encdirect"
# Scale: the service and its Sea_Area_Named_Water_Area layer.
ENC_LAYERS = {"coastal": ("enc_coastal", 175), "harbour": ("enc_harbour", 237)}
PAGE = 200


def get(url: str) -> bytes:
    for attempt in range(8):
        try:
            with urllib.request.urlopen(url, timeout=180) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            if attempt == 7:
                raise
            print(f"retry {url}: {e}", file=sys.stderr)
            time.sleep(3 + 4 * attempt)
    raise AssertionError


def get_json(url: str) -> dict:
    """ENC Direct answers a stopped service with an error in an ordinary response: retried as a failure."""
    for attempt in range(10):
        d = json.loads(get(url))
        if "error" not in d:
            return d
        if attempt == 9:
            raise SystemExit(f"{url}: {d['error']}")
        print(f"retry {url}: {d['error'].get('message')}", file=sys.stderr)
        time.sleep(15 + 15 * attempt)
    raise AssertionError


def cgndb(cache: str, bbox: str):
    """Each CGNDB marine name with an outline in the box, under its English name."""
    os.makedirs(f"{cache}/cgndb", exist_ok=True)
    ids = []
    for concise in CGNDB_CONCISE:
        q = urllib.parse.urlencode({"bbox": bbox, "concise": concise, "num": 5000})
        path = f"{cache}/cgndb/listing-{concise}.json"
        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(get(f"{CGNDB}/geonames.json?{q}"))
        ids += [i["id"] for i in json.loads(open(path, "rb").read(), strict=False)["items"]]
    bad = [i for i in ids if not CGNDB_ID.match(i)]
    if bad:
        raise SystemExit(f"CGNDB returned ids it shouldn't: {bad[:5]}")

    def one(i: str) -> str:
        path = f"{cache}/cgndb/{i}.geojson"
        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(get(f"{CGNDB}/geonames/{i}.geojson"))
        return path

    with ThreadPoolExecutor(6) as pool:
        paths = list(pool.map(one, sorted(set(ids))))
    # One feature may carry several names, in English, French or an Indigenous language, each
    # its own file; it is kept once, under the name whose language is undetermined or English.
    order = {"und": 0, "eng": 1, "fra": 2}
    best = {}
    for path in paths:
        f = json.load(open(path))
        g = f.get("geometry") or {}
        if g.get("type") not in ("Polygon", "MultiPolygon"):
            continue
        p = f["properties"]
        rank = order.get(p.get("language"), 3)
        if p["featureid"] not in best or rank < best[p["featureid"]][0]:
            best[p["featureid"]] = (rank, p["name"], g)
    for _, name, g in best.values():
        yield {"name": name, "source": "cgndb", "scale": None}, shape(g)


def enc(cache: str, west: float, south: float, east: float, north: float):
    """Each chart's named sea area in the box, pieces of one name at one scale merged where they touch."""
    os.makedirs(f"{cache}/enc", exist_ok=True)
    envelope = json.dumps({"xmin": west, "ymin": south, "xmax": east, "ymax": north,
                           "spatialReference": {"wkid": 4326}})
    common = {"geometry": envelope, "geometryType": "esriGeometryEnvelope", "inSR": 4326,
              "spatialRel": "esriSpatialRelIntersects", "where": "1=1"}
    for scale, (service, layer) in ENC_LAYERS.items():
        path = f"{cache}/enc/{scale}.geojson"
        if not os.path.exists(path):
            url = f"{ENC}/{service}/MapServer/{layer}/query"
            meta = get_json(f"{ENC}/{service}/MapServer/{layer}?f=json")
            oid = next(f["name"] for f in meta["fields"] if f["type"] == "esriFieldTypeOID")
            total = get_json(url + "?" + urllib.parse.urlencode({**common, "returnCountOnly": "true", "f": "json"}))["count"]
            features, offset = [], 0
            while True:
                q = urllib.parse.urlencode({**common, "outFields": "OBJNAM," + oid, "outSR": 4326, "orderByFields": oid,
                                            "resultOffset": offset, "resultRecordCount": PAGE, "f": "geojson"})
                page = get_json(f"{url}?{q}")
                features += page["features"]
                offset += len(page["features"])
                if not page["features"] or (not page.get("exceededTransferLimit") and len(page["features"]) < PAGE):
                    break
            if len({f["properties"][oid] for f in features}) != total:
                raise SystemExit(f"ENC {scale}: fetched {len(features)} of {total} areas")
            with open(path, "w") as f:
                json.dump({"type": "FeatureCollection", "features": features}, f)
        pieces = defaultdict(list)
        for f in json.load(open(path))["features"]:
            name = (f["properties"].get("OBJNAM") or "").strip()
            if name and f.get("geometry"):
                pieces[re.sub(r"\s+", " ", name).lower()].append((name, shape(f["geometry"]).buffer(0)))
        for parts in pieces.values():
            # Merged by touching: the charts cut one area at each cell's edge.
            for g in getattr(unary_union([g for _, g in parts]), "geoms", None) or [unary_union([g for _, g in parts])]:
                yield {"name": parts[0][0], "source": "enc", "scale": scale}, g


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cache")
    ap.add_argument("out")
    ap.add_argument("--bbox", required=True)
    a = ap.parse_args()
    west, south, east, north = map(float, a.bbox.split(","))
    area = box(west, south, east, north)
    n = 0
    with open(a.out + ".new", "w") as out:
        for props, g in [*cgndb(a.cache, a.bbox), *enc(a.cache, west, south, east, north)]:
            g = g.intersection(area)
            if g.is_empty or not props["name"]:
                continue
            out.write(json.dumps({"type": "Feature", "properties": props, "geometry": mapping(g)}) + "\n")
            n += 1
    os.replace(a.out + ".new", a.out)
    print(f"{n} named water outlines")


if __name__ == "__main__":
    main()
