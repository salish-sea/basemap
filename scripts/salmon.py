# /// script
# requires-python = ">=3.12"
# dependencies = ["rasterio>=1.4", "numpy>=2", "shapely>=2"]
# ///
"""Which salmon and steelhead runs use each named river that reaches the sea (decisions/020).

  salmon.py fetch DIR
      downloads, into DIR, the reaches of Washington's streams where SWIFD records each run
      (WDFW and the Northwest Indian Fisheries Commission), as lines; the Makefile
      downloads NuSEDS's census sites in British Columbia beside it (Fisheries and Oceans
      Canada, Open Government Licence – Canada), as nuseds-sites.csv;
  salmon.py build DIR rivers.geojsons sea.geojsons dem.tif salmon.geojsons --bbox=W,S,E,N
      writes one GeoJSON point a line, at the mouth of each river that Protomaps names
      (rivers.geojsons, its river lines with their names) and that reaches the sea
      (sea.geojsons, Protomaps' marine water, which tells the sea from a lake), with the
      runs that use it as `runs`. The depth grid (dem.tif) says which way a stream flows.

Only facts per river are kept, never either dataset's records or geometry, as
SalishSea.io's rights policy requires (its §7.3, D-24).

Each river is labelled as a whole system: its tributaries' runs with its own, at the
mouth that reaches the sea. In Washington the system is built from SWIFD's lines, each
stream flowing into the stream its lower end touches, so the Green and the Black, which
meet at Tukwila, are the Duwamish's, labelled where it reaches Elliott Bay. (SWIFD's
stream identifiers can't be read as mouths: the Duwamish River's is halfway along it.) In
British Columbia the system is the province's hierarchical watershed code, labelled at
NuSEDS's point for the river nearest the sea.
"""

import argparse
import csv
import itertools
import json
import math
import re
import urllib.parse
import urllib.request

import numpy as np
import rasterio
from rasterio.windows import from_bounds
from shapely import STRtree
from shapely.geometry import MultiLineString, Point, shape
from shapely.ops import linemerge

SWIFD = "https://geodataservices.wdfw.wa.gov/arcgis/rest/services/MapServices/SWIFD/MapServer/0/query"
# SWIFD's evidence that a run uses a stream: seen there, including where hatchery fish or
# fish carried past a dam are; not presumed, modelled, potential or historic.
DOCUMENTED = ("Documented", "Artificial - Documented", "Transported - Documented")
SPECIES = ("Chinook Salmon", "Coho Salmon", "Chum Salmon", "Pink Salmon", "Sockeye Salmon", "Steelhead Trout")
# Each run as (species, timing), from SWIFD's names and NuSEDS's codes. Chinook's timing in
# NuSEDS is in its conservation unit's name: "COWICHAN AND KOKSILAH_FA_0.x" is a fall run.
SWIFD_RUNS = {
    "Spring Chinook": ("Chinook", "spring"), "Summer Chinook": ("Chinook", "summer"), "Fall Chinook": ("Chinook", "fall"),
    "Coho": ("coho", None),
    "Summer Chum": ("chum", "summer"), "Fall Chum": ("chum", "fall"), "Winter Chum": ("chum", "winter"),
    "Pink Odd Year": ("pink", "odd years"), "Pink Even Year": ("pink", "even years"),
    "Sockeye": ("sockeye", None),
    "Summer Steelhead": ("steelhead", "summer"), "Winter Steelhead": ("steelhead", "winter"),
}
NUSEDS_SPECIES = {"CK": "Chinook", "CO": "coho", "CM": "chum", "PKO": "pink", "PKE": "pink", "SEL": "sockeye", "SER": "sockeye"}
CHINOOK_TIMING = {"SP": "spring", "SU": "summer", "FA": "fall"}
ORDER = ["Chinook", "coho", "chum", "pink", "sockeye", "steelhead"]
TIMING_ORDER = ["spring", "summer", "fall", "winter", "odd years", "even years"]
# A Washington river system reaches the sea when its outlet ends within SEA_NEAR degrees,
# about 3 km, of Protomaps' marine water, which tells the sea from a lake: the depth grid
# can't, as Lake Washington's bed is below sea level in it. Far enough to cross the flats
# off a delta, as the Skagit's, the Snohomish's and the Nisqually's mouths need; a
# tributary is no outlet, so the Green, ending at Tukwila, is the Duwamish's. A British Columbia river is told
# by its watershed code instead (`reaches_sea`). LOW_WITHIN is how far round a British
# Columbia census site the depth grid is read, to put the label at the site nearest the sea.
SEA_NEAR = 0.03
LOW_WITHIN = 300
# A stream that ends away from the sea and any stream, as the Cedar's route does across Lake
# Washington, flows into the nearest stream within this many degrees, about 1 km: the Cedar
# into the Ship Canal, 330 m away across the water.
LAKE_JOIN = 0.012
# The names of rivers and creeks; a delta's channels, such as Hat Slough and West Pass,
# are part of their river, not rivers of their own.
RIVER_NAME = re.compile(r" (River|Creek|Stream|Brook)$")
# A river's label appears from a zoom set by how long it is on the map, in kilometres: the
# Fraser and the Skagit at 10, a short creek at 12.
ZOOMS_BY_LENGTH = [(40, 10), (12, 11), (0, 12)]
# A fork of a river, such as the Skagit's North Fork. Where a river ends at the head of
# its delta and its forks reach the sea, as the Skagit's do, its label is at a fork's
# mouth, with the runs of the river and its forks together.
FORK = re.compile(r"^(North|South|Middle|East|West) Fork ")
# Systems of one name are one river when their mouths are within this many kilometres, as
# the Skagit's forks' and the Stillaguamish's channels' are, so that a North Fork Bear
# Creek's system isn't taken for every Bear Creek's.
FORK_WITHIN = 15
# A stream's lower end flows into another stream whose line is within this many degrees of
# it, about 50 m, as SWIFD's lines are simplified to about 30 m when fetched.
TOUCH = 0.0006
SIMPLIFY = 0.0003


def fetch_swifd() -> list[dict]:
    where = (f"SPECIES IN ({','.join(repr(s) for s in SPECIES)}) "
             f"AND DISTTYPE_DESC IN ({','.join(repr(d) for d in DOCUMENTED)})").replace('"', "'")
    features, offset = [], 0
    while True:
        query = urllib.parse.urlencode({
            "where": where, "outFields": "LLID,LLID_STRM_NAME,SPECIESRUN", "outSR": 4326,
            "maxAllowableOffset": SIMPLIFY, "geometryPrecision": 5,
            "orderByFields": "OBJECTID", "resultOffset": offset, "f": "geojson",
        })
        with urllib.request.urlopen(f"{SWIFD}?{query}", timeout=300) as response:
            page = json.load(response)
        if "error" in page:
            raise SystemExit(f"SWIFD: {page['error']}")
        features += page["features"]
        if not page.get("exceededTransferLimit") and not page.get("properties", {}).get("exceededTransferLimit"):
            return features
        offset = len(features)


def fetch(out: str) -> None:
    features = fetch_swifd()
    with open(f"{out}/swifd.geojson", "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f)
    print(f"SWIFD: {len(features)} reaches with salmon or steelhead runs")


def folded(name: str) -> str:
    return re.sub(r"\s+", " ", name.casefold().replace("’", "'")).strip()


def label(runs: set[tuple[str, str | None]]) -> str:
    """'Chinook (spring, fall) · coho · pink (odd years)'."""
    parts = []
    for species in ORDER:
        timings = sorted({t for s, t in runs if s == species and t}, key=TIMING_ORDER.index)
        if timings[-2:] == ["odd years", "even years"]:
            timings[-2:] = ["odd and even years"]
        if any(s == species for s, _ in runs):
            parts.append(f"{species} ({', '.join(timings)})" if timings else species)
    return " · ".join(parts)


class Sea:
    """Whether a Washington river's mouth reaches salt water, by the depth grid."""

    def __init__(self, path: str):
        self.dem = rasterio.open(path)

    def lowest(self, lon: float, lat: float, metres: float) -> float:
        dlat = metres / 110540
        dlon = metres / (111320 * math.cos(math.radians(lat)))
        nodata = self.dem.nodata if self.dem.nodata is not None else -99999
        try:
            window = from_bounds(lon - dlon, lat - dlat, lon + dlon, lat + dlat, self.dem.transform)
            cells = self.dem.read(1, window=window, boundless=True, fill_value=nodata)
        except ValueError:
            return math.inf
        cells = cells[cells != nodata]
        return float(np.nanmin(cells)) if cells.size else math.inf


class Marine:
    """Whether a point is near the sea, by Protomaps' marine water."""

    def __init__(self, path: str):
        polygons = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip("\x1e \n")
                if line:
                    polygons.append(shape(json.loads(line)["geometry"]).buffer(0))
        self.tree = STRtree(polygons)
        self.polygons = polygons

    def near(self, lon: float, lat: float) -> bool:
        point = Point(lon, lat)
        return any(self.polygons[i].distance(point) <= SEA_NEAR for i in self.tree.query(point.buffer(SEA_NEAR)))


# The province's codes for the great rivers that reach the sea in or beside it: the Fraser,
# the Skeena, the Nass, the Stikine and the Taku. The Peace (200) and the Columbia (300)
# reach the sea elsewhere, so their parts in the province aren't labelled.
SEA_GOING = {"100", "400", "500", "600", "700"}


def reaches_sea(code: str) -> bool:
    """Whether a British Columbia watershed code is a river that reaches the sea: one of the
    great rivers, such as the Fraser, 100, or the Skeena, 400; or a coastal drainage's own
    river, a single group in the 900s, such as the Alsek, 990; or a stream one level below a
    coastal drainage, as the Cowichan, 920-252823, is. A deeper code is a tributary, as the
    Harrison, 100-077501, is."""
    groups = code.split("-")
    return (len(groups) == 1 and (code in SEA_GOING or code.startswith("9"))) or (groups[0].startswith("9") and len(groups) == 2)


def washington(src: str, named: dict[str, float], sea: "Sea", marine: Marine, inside) -> list[dict]:
    """Washington's labelled rivers, each a system of SWIFD's streams with its runs and the
    point where its outlet reaches the sea."""
    streams: dict[str, dict] = {}
    with open(f"{src}/swifd.geojson", encoding="utf-8") as f:
        for feature in json.load(f)["features"]:
            p, g = feature["properties"], feature["geometry"]
            llid, run = str(p.get("LLID") or ""), SWIFD_RUNS.get(p.get("SPECIESRUN"))
            if not llid or not g:
                continue
            stream = streams.setdefault(llid, {"name": p.get("LLID_STRM_NAME") or "", "runs": set(), "lines": []})
            if run:
                stream["runs"].add(run)
            parts = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
            stream["lines"] += [part for part in parts if len(part) >= 2]
    keys = [k for k, s_ in streams.items() if s_["lines"]]
    for key in keys:
        stream = streams[key]
        merged = linemerge(MultiLineString(stream["lines"]))
        stream["geometry"] = merged
        ends = [pt for part in getattr(merged, "geoms", [merged]) for pt in (part.coords[0], part.coords[-1])]
        # The end near the sea, if only one is, is where the stream flows out; otherwise the
        # lower, by the depth grid. The sea comes first because the grid holds lake beds: the
        # Ship Canal's end in Lake Washington is lower than its end at the Ballard Locks.
        seaward = [e for e in ends if marine.near(*e)]
        if seaward and len(seaward) < len(ends):
            ends = seaward
        stream["out"] = Point(min(ends, key=lambda e: sea.lowest(e[0], e[1], 100)))
    tree = STRtree([streams[k]["geometry"] for k in keys])
    into: dict[str, str] = {}
    for i, key in enumerate(keys):
        out_ = streams[key]["out"]
        near = [keys[j] for j in tree.query(out_.buffer(TOUCH)) if keys[j] != key]
        # A stream ending at the same point flows on with it, as the Black does beside the Green.
        near = [k for k in near if streams[k]["geometry"].distance(out_) <= TOUCH and streams[k]["out"].distance(out_) > TOUCH]
        if near:
            into[key] = min(near, key=lambda k: streams[k]["geometry"].distance(out_))
    # A stream ending away from the sea and any stream flows on into the nearest within
    # LAKE_JOIN, as across a lake.
    for key in keys:
        out_ = streams[key]["out"]
        if key in into or marine.near(out_.x, out_.y):
            continue
        near = [keys[j] for j in tree.query(out_.buffer(LAKE_JOIN)) if keys[j] != key]
        near = [k for k in near if streams[k]["out"].distance(out_) > TOUCH and streams[k]["geometry"].distance(out_) <= LAKE_JOIN]
        if near:
            into[key] = min(near, key=lambda k: streams[k]["geometry"].distance(out_))

    def outlet(key: str) -> str:
        seen = set()
        while key in into and key not in seen:
            seen.add(key)
            key = into[key]
        return key

    systems: dict[str, list[str]] = {}
    for key in keys:
        systems.setdefault(outlet(key), []).append(key)

    def name_of(outlet_key: str, members: list[str]) -> str | None:
        """The river with a name on the map nearest the outlet, a fork named for its river."""
        upstream: dict[str, list[str]] = {}
        for k in members:
            if k in into:
                upstream.setdefault(into[k], []).append(k)
        # Level by level from the outlet; of the named rivers at the nearest level, the longest,
        # so that the Lake Washington system, through the Ship Canal, is the Cedar's.
        level, seen = [outlet_key], set()
        while level:
            found = []
            for k in level:
                name = streams[k]["name"]
                for candidate in (FORK.sub("", name), name):
                    if RIVER_NAME.search(candidate) and folded(candidate) in named:
                        found.append(candidate)
                        break
            if found:
                return max(found, key=lambda n: named[folded(n)])
            seen.update(level)
            level = [u for k in level for u in upstream.get(k, []) if u not in seen]
        return None

    rivers: list[dict] = []
    for outlet_key, members in systems.items():
        name = name_of(outlet_key, members)
        if not name:
            continue
        mouth = streams[outlet_key]["out"]
        # How long the system is on the map: its longest named river, as the Green is the Duwamish's.
        km = max((named.get(folded(n), 0) for k in members for n in (streams[k]["name"], FORK.sub("", streams[k]["name"]))), default=0)
        river = {"name": name, "runs": set().union(*(streams[k]["runs"] for k in members)), "mouths": [(mouth.x, mouth.y)], "km": km}
        # Systems of one name with mouths close together are one river: the Skagit's forks.
        for other in rivers:
            if folded(other["name"]) == folded(name) and any(
                    math.hypot((a[0] - b[0]) * 111.32 * math.cos(math.radians(a[1])), (a[1] - b[1]) * 110.54) <= FORK_WITHIN
                    for a in other["mouths"] for b in river["mouths"]):
                other["runs"] |= river["runs"]
                other["mouths"] += river["mouths"]
                other["km"] = max(other["km"], river["km"])
                break
        else:
            rivers.append(river)
    out = []
    for river in rivers:
        reaching = [m for m in river["mouths"] if inside(*m) and marine.near(*m)]
        if reaching:
            river["lon"], river["lat"] = reaching[0]
            out.append(river)
    return out


def build(src: str, rivers_path: str, sea_path: str, dem: str, out: str, bbox: tuple[float, float, float, float]) -> None:
    west, south, east, north = bbox
    inside = lambda lon, lat: west <= lon <= east and south <= lat <= north
    # The rivers the map names, and how long each is on the map, in kilometres. A line cut
    # at a tile's edge is counted in each tile, which makes no difference to the zoom.
    named: dict[str, float] = {}
    with open(rivers_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip("\x1e \n")
            if not line:
                continue
            feature = json.loads(line)
            name, g = feature["properties"].get("name"), feature["geometry"]
            if not name or not g:
                continue
            lines = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]] if g["type"] == "LineString" else []
            km = sum(math.hypot((b[0] - a[0]) * 111.32 * math.cos(math.radians(a[1])), (b[1] - a[1]) * 110.54)
                     for line_ in lines for a, b in itertools.pairwise(line_))
            named[folded(name)] = named.get(folded(name), 0) + km
    sea = Sea(dem)
    # Each river: its name as the map writes it, its mouth, and its runs.
    rivers: dict[tuple[str, str], dict] = {}

    # A British Columbia river's runs are every population in its watershed: the province's
    # watershed code is hierarchical, so the Harrison's, 100-077501, is within the Fraser's, 100.
    trimmed = lambda code: re.sub(r"(-0+)*-?$", "", code or "")
    with open(f"{src}/nuseds-sites.csv", encoding="utf-8-sig", errors="replace") as f:
        sites = list(csv.DictReader(f))
    populations = []
    for row in sites:
        species = NUSEDS_SPECIES.get(row["SPECIES_QUALIFIED"])
        if not species:
            continue
        timing = None
        if species == "Chinook":
            found = re.search(r"_(SP|SU|FA)(?:_|$)", row["CU_NAME"] or "")
            timing = CHINOOK_TIMING[found.group(1)] if found else None
        elif species == "pink":
            timing = "odd years" if row["SPECIES_QUALIFIED"] == "PKO" else "even years"
        populations.append((trimmed(row["FWA_WATERSHED_CDE"]), (species, timing)))
    for row in sites:
        name = row["CENSUS_SITE"].title().replace("'S", "'s")
        code = trimmed(row["FWA_WATERSHED_CDE"])
        if folded(name) not in named or not RIVER_NAME.search(name) or not reaches_sea(code) or not row["Y_LAT"] or not row["X_LONGT"]:
            continue
        # A river is its watershed code: two streams of one name are two rivers.
        river = rivers.setdefault(("bc", code), {"name": name, "points": [], "runs": set(), "code": code})
        river["points"].append((float(row["X_LONGT"]), float(row["Y_LAT"])))
    for (country, _), river in rivers.items():
        if country == "bc":
            code = river["code"]
            river["runs"] = {run for c, run in populations if c == code or c.startswith(code + "-")}

    for i, river in enumerate(washington(src, named, sea, Marine(sea_path), inside)):
        rivers[("wa", str(i))] = river

    written = 0
    with open(out, "w", encoding="utf-8") as f:
        for key, river in sorted(rivers.items(), key=lambda r: r[1]["name"]):
            if key[0] == "bc":
                # Its census site nearest the sea is where the label goes.
                points = [p for p in river["points"] if inside(*p)]
                if not points:
                    continue
                river["lon"], river["lat"] = min(points, key=lambda p: sea.lowest(*p, LOW_WITHIN))
            elif folded(river["name"]) not in named:
                continue
            # A run named only by its species when another record names its timing adds nothing.
            runs = {r for r in river["runs"] if r[1] or not any(s == r[0] and t for s, t in river["runs"])}
            length = river.get("km", named[folded(river["name"])])
            minzoom = next(z for km, z in ZOOMS_BY_LENGTH if length >= km)
            f.write(json.dumps({
                "type": "Feature", "properties": {"name": river["name"], "runs": label(runs), "min_zoom": minzoom},
                "geometry": {"type": "Point", "coordinates": [round(river["lon"], 5), round(river["lat"], 5)]},
                "tippecanoe": {"minzoom": min(minzoom, 14)},
            }, ensure_ascii=False) + "\n")
            written += 1
    print(f"{out}: {written} rivers with salmon runs")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="step", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("dir")
    b = sub.add_parser("build")
    for arg in ("dir", "rivers", "sea", "dem", "out"):
        b.add_argument(arg)
    b.add_argument("--bbox", required=True)
    args = parser.parse_args()
    if args.step == "fetch":
        fetch(args.dir)
    else:
        build(args.dir, args.rivers, args.sea, args.dem, args.out, tuple(float(x) for x in args.bbox.split(",")))


if __name__ == "__main__":
    main()
