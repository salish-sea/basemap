# /// script
# requires-python = ">=3.12"
# dependencies = ["shapely>=2", "pyogrio>=0.10", "pyproj>=3.7", "numpy>=2"]
# ///
"""The land the water regions leave out (decisions/027), from open government data only.

The depth grid's zero isn't the shore: diked farmland in the Fraser, Skagit and Columbia
lowlands lies below it. So the regions subtract the land as the charts and the province
draw it: NOAA's electronic charts' land areas (S-57 LNDARE, through ENC Direct, public
domain) for US waters, and British Columbia's terrestrial boundary (the province drawn to its
shoreline, from the Freshwater Atlas; Open Government Licence – British Columbia) for BC.

    uv run scripts/region_land.py CACHEDIR BC_BOUNDARY.gpkg.zip OUT.geojsons --bbox=W,S,E,N

Downloads the charts' land areas into CACHEDIR once, and writes one land polygon per line,
its `source` "noaa" or "bc"; and, as `source` "lock", the charts' lock gates and lock basins,
widened by about 30 m, which the regions treat as the end of salt water.
"""

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request

import numpy as np
import pyogrio
import pyogrio.raw
from pyproj import Transformer
from shapely import box, from_wkb, transform
from shapely.geometry import mapping, shape

ENC = "https://encdirect.noaa.gov/arcgis/rest/services/encdirect"
# Scale: the service and its Land_Area layer.
ENC_LAND = {"coastal": ("enc_coastal", 171), "harbour": ("enc_harbour", 233)}
# Where salt water ends at a lock (the Ballard Locks): the charts' lock gates and lock basins,
# which the regions treat as a barrier, so a lake behind a lock never reaches the sea.
ENC_LOCKS = {"gates": ("enc_harbour", 121), "lock-basins": ("enc_harbour", 181)}
PAGE = 200
BC_LAYER = "BC_Boundary_Terrestrial_Singlepart"


def get_json(url: str) -> dict:
    """ENC Direct answers a stopped service with an error in an ordinary response: retried as a failure."""
    for attempt in range(10):
        try:
            with urllib.request.urlopen(url, timeout=180) as r:
                d = json.load(r)
            if "error" not in d:
                return d
            problem = d["error"].get("message")
        except Exception as e:  # noqa: BLE001
            problem = e
        if attempt == 9:
            raise SystemExit(f"{url}: {problem}")
        print(f"retry {url}: {problem}", file=sys.stderr)
        time.sleep(15 + 15 * attempt)
    raise AssertionError


def chart_layers(cache: str, layers: dict, west: float, south: float, east: float, north: float):
    """Each layer's features in the box, from ENC Direct, downloaded into CACHE once."""
    os.makedirs(cache, exist_ok=True)
    envelope = json.dumps({"xmin": west, "ymin": south, "xmax": east, "ymax": north, "spatialReference": {"wkid": 4326}})
    common = {"geometry": envelope, "geometryType": "esriGeometryEnvelope", "inSR": 4326,
              "spatialRel": "esriSpatialRelIntersects", "where": "1=1"}
    for scale, (service, layer) in layers.items():
        path = f"{cache}/{scale}.geojson"
        if not os.path.exists(path):
            url = f"{ENC}/{service}/MapServer/{layer}/query"
            meta = get_json(f"{ENC}/{service}/MapServer/{layer}?f=json")
            oid = next(f["name"] for f in meta["fields"] if f["type"] == "esriFieldTypeOID")
            total = get_json(url + "?" + urllib.parse.urlencode({**common, "returnCountOnly": "true", "f": "json"}))["count"]
            features, offset = [], 0
            while True:
                q = urllib.parse.urlencode({**common, "outFields": oid, "outSR": 4326, "orderByFields": oid,
                                            "resultOffset": offset, "resultRecordCount": PAGE, "f": "geojson"})
                page = get_json(f"{url}?{q}")
                features += page["features"]
                offset += len(page["features"])
                if not page["features"] or (not page.get("exceededTransferLimit") and len(page["features"]) < PAGE):
                    break
            if len({f["properties"][oid] for f in features}) != total:
                raise SystemExit(f"ENC {scale}: fetched {len(features)} of {total} features")
            # Written aside and renamed once complete, so a failed download leaves nothing behind.
            with open(path + ".part", "w") as f:
                json.dump({"type": "FeatureCollection", "features": features}, f)
            os.replace(path + ".part", path)
        for f in json.load(open(path))["features"]:
            if f.get("geometry"):
                yield shape(f["geometry"])


def bc_land(gpkg_zip: str, area):
    """The province's land, clipped to the box: its polygons in BC Albers, brought to lon/lat."""
    to_lonlat = Transformer.from_crs(3005, 4326, always_xy=True)
    to_albers = Transformer.from_crs(4326, 3005, always_xy=True)
    west, south, east, north = area.bounds
    xs, ys = to_albers.transform([west, east, west, east], [south, south, north, north])
    path = f"/vsizip/{os.path.abspath(gpkg_zip)}/BC_Boundary_Terrestrial.gpkg"
    _, _, wkb, _ = pyogrio.raw.read(path, layer=BC_LAYER, bbox=(min(xs), min(ys), max(xs), max(ys)), columns=[])
    for g in from_wkb(wkb):
        # About 10 m: the grid the regions are worked out on is 90 m.
        yield transform(g.simplify(10), lambda c: np.column_stack(to_lonlat.transform(c[:, 0], c[:, 1])))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cache")
    ap.add_argument("bc")
    ap.add_argument("out")
    ap.add_argument("--bbox", required=True)
    a = ap.parse_args()
    west, south, east, north = map(float, a.bbox.split(","))
    area = box(west, south, east, north)
    n = 0
    with open(a.out + ".new", "w") as out:
        locks = (g.buffer(0.0003) for g in chart_layers(a.cache, ENC_LOCKS, west, south, east, north))
        for source, geoms in (("noaa", chart_layers(a.cache, ENC_LAND, west, south, east, north)),
                              ("bc", bc_land(a.bc, area)), ("lock", locks)):
            for g in geoms:
                g = g.buffer(0).intersection(area)
                if not g.is_empty:
                    out.write(json.dumps({"type": "Feature", "properties": {"source": source}, "geometry": mapping(g)}) + "\n")
                    n += 1
    os.replace(a.out + ".new", a.out)
    print(f"{n} land polygons")


if __name__ == "__main__":
    main()
