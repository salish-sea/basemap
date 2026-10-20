# /// script
# requires-python = ">=3.12"
# dependencies = ["rasterio>=1.4", "numpy>=2"]
# ///
"""Which salmon and steelhead runs use each named river that reaches the sea (decisions/020).

  salmon.py fetch DIR
      downloads, into DIR, the runs SWIFD records on each Washington stream (WDFW and the
      Northwest Indian Fisheries Commission); the Makefile downloads NuSEDS's census sites
      in British Columbia beside it (Fisheries and Oceans Canada, Open Government
      Licence – Canada), as nuseds-sites.csv;
  salmon.py build DIR rivers.geojsons dem.tif salmon.geojsons --bbox=W,S,E,N
      writes one GeoJSON point a line, at the mouth of each river that Protomaps names
      (rivers.geojsons, its river lines with their names and zooms) and that reaches salt
      water by the depth grid (dem.tif), with the runs that use it as `runs`.

Only facts per river are kept, never either dataset's records or geometry, as
SalishSea.io's rights policy requires (its §7.3, D-24).

A Washington river's mouth is in its stream identifier, the LLID, which is the
longitude and latitude of the mouth: 1223661483874 is 122.3661°W, 48.3874°N, the
Skagit's. A British Columbia river's is NuSEDS's point for it nearest the sea; each
population is placed at the mouth of the stream it uses.
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
# A Washington river reaches salt water when its mouth is low and there is open water near
# it, by the depth grid: the ground within LOW_WITHIN metres of the mouth comes as low as
# LOW, and water within SEA_WITHIN metres is SEA_DEPTH deep, far enough to cross the flats
# off a delta. The Bear Creeks, whose mouths are 90 m up, fail; the Snohomish passes. A
# British Columbia river is told by its watershed code instead (`reaches_sea`).
LOW_WITHIN, LOW = 300, 5
SEA_WITHIN, SEA_DEPTH = 8000, -1
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
# A fork belongs to the river of its name whose mouth is within this many kilometres of its
# own, so that a North Fork Bear Creek isn't taken for a fork of every Bear Creek. The
# Skagit's North Fork reaches the sea 8.2 km from where the Skagit itself ends.
FORK_WITHIN = 15


def fetch_swifd() -> list[dict]:
    where = (f"SPECIES IN ({','.join(repr(s) for s in SPECIES)}) "
             f"AND DISTTYPE_DESC IN ({','.join(repr(d) for d in DOCUMENTED)})").replace('"', "'")
    rows, offset = [], 0
    while True:
        query = urllib.parse.urlencode({
            "where": where, "outFields": "LLID,LLID_STRM_NAME,SPECIESRUN", "returnGeometry": "false",
            "returnDistinctValues": "true", "orderByFields": "LLID,SPECIESRUN", "resultOffset": offset, "f": "json",
        })
        with urllib.request.urlopen(f"{SWIFD}?{query}", timeout=300) as response:
            page = json.load(response)
        if "error" in page:
            raise SystemExit(f"SWIFD: {page['error']}")
        rows += [f["attributes"] for f in page["features"]]
        if not page.get("exceededTransferLimit"):
            return rows
        offset = len(rows)


def fetch(out: str) -> None:
    rows = fetch_swifd()
    with open(f"{out}/swifd.json", "w", encoding="utf-8") as f:
        json.dump(rows, f)
    print(f"SWIFD: {len(rows)} runs on streams")


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

    def reaches(self, lon: float, lat: float) -> bool:
        return self.lowest(lon, lat, LOW_WITHIN) <= LOW and self.lowest(lon, lat, SEA_WITHIN) <= SEA_DEPTH


def reaches_sea(code: str) -> bool:
    """Whether a British Columbia watershed code is a river that reaches the sea: the
    Fraser itself, 100, or a stream one level below a coastal drainage, as the Cowichan,
    920-252823, is. A deeper code is a tributary, as the Harrison, 100-077501, is."""
    groups = code.split("-")
    return groups == ["100"] or (groups[0].startswith("9") and len(groups) == 2)


def build(src: str, rivers_path: str, dem: str, out: str, bbox: tuple[float, float, float, float]) -> None:
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

    with open(f"{src}/swifd.json", encoding="utf-8") as f:
        for row in json.load(f):
            name, llid, run = row["LLID_STRM_NAME"], str(row["LLID"] or ""), SWIFD_RUNS.get(row["SPECIESRUN"])
            if not name or not run or not re.fullmatch(r"\d{13}", llid) or not RIVER_NAME.search(name):
                continue
            if folded(name) not in named and folded(FORK.sub("", name)) not in named:
                continue
            lon, lat = -int(llid[:7]) / 10000, int(llid[7:]) / 10000
            river = rivers.setdefault(("wa", llid), {"name": name, "lon": lon, "lat": lat, "runs": set()})
            river["runs"].add(run)

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

    # Washington: a river that ends inland takes the mouth of a fork that reaches the sea,
    # and its forks' runs; a fork whose river is labelled is not labelled itself.
    reached = {key: inside(r["lon"], r["lat"]) and sea.reaches(r["lon"], r["lat"]) for key, r in rivers.items() if key[0] == "wa"}
    by_name: dict[str, list[tuple]] = {}
    for key, r in rivers.items():
        if key[0] == "wa":
            by_name.setdefault(folded(r["name"]), []).append(key)
    for key, fork in rivers.items():
        if key[0] != "wa" or not FORK.match(fork["name"]):
            continue
        parents = [p for p in by_name.get(folded(FORK.sub("", fork["name"])), [])
                   if math.hypot((rivers[p]["lon"] - fork["lon"]) * 111.32 * math.cos(math.radians(fork["lat"])),
                                 (rivers[p]["lat"] - fork["lat"]) * 110.54) <= FORK_WITHIN]
        for parent in parents:
            rivers[parent]["runs"] |= fork["runs"]
            if not reached[parent] and reached[key]:
                rivers[parent]["lon"], rivers[parent]["lat"] = fork["lon"], fork["lat"]
                reached[parent] = True
        if parents:
            reached[key] = False

    written = 0
    with open(out, "w", encoding="utf-8") as f:
        for key, river in sorted(rivers.items(), key=lambda r: r[1]["name"]):
            if key[0] == "bc":
                # Its census site nearest the sea is where the label goes.
                points = [p for p in river["points"] if inside(*p)]
                if not points:
                    continue
                river["lon"], river["lat"] = min(points, key=lambda p: sea.lowest(*p, LOW_WITHIN))
            elif not reached[key] or folded(river["name"]) not in named:
                continue
            # A run named only by its species when another record names its timing adds nothing.
            runs = {r for r in river["runs"] if r[1] or not any(s == r[0] and t for s, t in river["runs"])}
            minzoom = next(z for km, z in ZOOMS_BY_LENGTH if named[folded(river["name"])] >= km)
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
    for arg in ("dir", "rivers", "dem", "out"):
        b.add_argument(arg)
    b.add_argument("--bbox", required=True)
    args = parser.parse_args()
    if args.step == "fetch":
        fetch(args.dir)
    else:
        build(args.dir, args.rivers, args.dem, args.out, tuple(float(x) for x in args.bbox.split(",")))


if __name__ == "__main__":
    main()
