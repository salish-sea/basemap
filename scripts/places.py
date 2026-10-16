# /// script
# requires-python = ">=3.12"
# dependencies = ["osmium>=4"]
# ///
"""Writes the places a site's search offers, from the names the map labels (decisions/018).

Two lists, kept apart because their licences differ:

  places.py gazetteers names.geojsons places-gazetteers.json
      the water bodies and points that scripts/names.py chose from GNIS and CGNDB
      (decisions/006), at the positions and zooms the map labels them;
  places.py osm places-osm.json extract.osm.pbf ... --bbox=W,S,E,N
      the islands, towns and ferry terminals that OpenStreetMap names, which reach the
      map through Protomaps' tiles.

Only the Salish Sea's larger places are listed: water and points the map labels by zoom
12, islands that fit at zoom 13, cities, towns and villages, and one ferry terminal for
each landing the map's ferry routes reach. That is a couple of thousand names a person
might search for, not the tens of thousands the map labels.

Each list is one JSON object: what it holds, its licence and the attribution it needs,
and its places, each a row of the columns it names. A place's position is where to look
and its zoom how close: for a water body or a point, where and from what zoom the map
labels it; for an island, the middle of its outline and the zoom that fits all of it.
"""

import argparse
import itertools
import json
import math
import re

COLUMNS = ["name", "kind", "lon", "lat", "zoom", "other_names"]

GAZETTEERS = {
    "about": "Names of the Salish Sea's water and of points on it, as the basemap labels them by zoom 12",
    "sources": [
        "Geographic Names Information System, U.S. Geological Survey (public domain)",
        "Canadian Geographical Names Database, Natural Resources Canada (Open Government Licence – Canada)",
    ],
    "licence": "Public domain in the US; Canadian names under the Open Government Licence – Canada",
    "attribution": "Contains information licensed under the Open Government Licence – Canada",
}
OSM = {
    "about": "The Salish Sea's larger islands, its cities, towns and villages, and its ferry terminals, as OpenStreetMap names them",
    "sources": ["OpenStreetMap"],
    "licence": "Open Database License (ODbL) 1.0",
    "attribution": "© OpenStreetMap contributors",
}

# The kinds kept from OpenStreetMap, by tag, and the zoom to show a point at. An island
# drawn as an outline is shown whole instead. Hamlets, suburbs and neighbourhoods are
# left out: there are thousands, and few are where anyone reports from.
OSM_KINDS = {
    ("place", "city"): 11,
    ("place", "town"): 12,
    ("place", "village"): 13,
    # An island drawn only as a point is a rock or a small island: large ones are outlined.
    # Islets and such islands are labelled from zoom 15 and are left out (SMALLEST_ISLAND).
    ("place", "island"): 15,
    ("place", "islet"): 15,
    ("amenity", "ferry_terminal"): 15,
}
# Where a search looks: SalishSea.io's Salish Sea region (its src/extents.ts).
SEARCH_AREA = (-126.0, 47.0, -122.0, 50.5)
# The last zoom at which a water body or point the map labels is listed. Coves, and
# points inside them, appear later.
LAST_WATER_ZOOM = 12
# The smallest island listed: one that fits the map at this zoom. Hat Island is 13.
SMALLEST_ISLAND = 13
# Ferry terminals (landings()): how far from a route one may be, in metres; how close
# two must be to be one landing; the names that are a berth's, not a landing's; and the
# words that say nothing about which landing a name means.
ROUTE_REACH = 1000
LANDING = 800
BERTH = re.compile(r"\b(Berth|Slip|Foot Access|Level|Building)\b")
BERTH_AND_AFTER = re.compile(r"\s*\b(Berth|Slip)\b.*$")
NOT_A_LANDING = re.compile(r"[&,]|\bRoute\b")
GENERIC_WORDS = {"ferry", "ferries", "terminal", "dock", "landing", "berth", "foot", "access", "passenger", "water", "taxi",
                 "island", "the", "and"}
OUTLINED = {"island", "islet"}
# Settlements are drawn as points; an outline tagged as a town is the town's boundary,
# which repeats its point, so only islands and ferry terminals are read from outlines.
FROM_OUTLINES = {"island", "islet", "ferry_terminal"}
# How much of the map an island fills when shown whole: its longer side, in 512-pixel tiles;
# a map is usually wider than one tile, so this leaves room around it.
FIT = 1.0
ZOOMS = (6, 16)
OTHER_NAME_TAGS = ("alt_name", "short_name", "official_name", "name:en")
# Two records of one kind and name this close, in degrees, are one place: a ferry
# terminal drawn as a point and an outline, or an island as a point and an outline.
SAME = 0.01
# Outlines of one kind and name this close are one group, as each of the Trail Islands
# is an outline named for the group, and are listed once, shown whole.
GROUP = 0.05


def rounded(x: float) -> float:
    """Five decimal places, about a metre."""
    return round(x, 5)


def searched(place: list) -> bool:
    """Whether a place is one the search offers: in the Salish Sea, and big enough."""
    _, kind, lon, lat, zoom, _ = place
    west, south, east, north = SEARCH_AREA
    if not (west <= lon <= east and south <= lat <= north):
        return False
    if kind in ("water", "point"):
        return zoom <= LAST_WATER_ZOOM
    if kind in ("island", "islet"):
        return kind == "island" and zoom <= SMALLEST_ISLAND
    return True


def write(path: str, header: dict, places: list[list]) -> None:
    places = [p for p in places if searched(p)]
    places.sort(key=lambda p: (p[0].casefold(), p[1], p[3], p[2]))
    with open(path, "w", encoding="utf-8") as f:
        json.dump({**header, "columns": COLUMNS, "places": places}, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")


def gazetteers(names: str, out: str) -> None:
    places = []
    with open(names, encoding="utf-8") as f:
        for line in f:
            feature = json.loads(line)
            p = feature["properties"]
            lon, lat = feature["geometry"]["coordinates"]
            places.append([p["name"], p["kind"], rounded(lon), rounded(lat), p["minzoom"], []])
    write(out, GAZETTEERS, places)


def fit_zoom(west: float, south: float, east: float, north: float) -> int:
    """The zoom at which a box's longer side spans FIT of a tile."""
    y = lambda lat: math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    span = max((east - west) / 360, (y(north) - y(south)) / (2 * math.pi))
    if span <= 0:
        return ZOOMS[1]
    return max(ZOOMS[0], min(ZOOMS[1], math.floor(math.log2(FIT / span))))


def tag_of(tags) -> tuple[str, str] | None:
    """The tag that makes a record one of the kinds kept, if it is."""
    for key in ("place", "amenity"):
        if (key, tags.get(key)) in OSM_KINDS:
            return (key, tags.get(key))
    return None


def other_names(tags, name: str) -> list[str]:
    names = []
    for key in OTHER_NAME_TAGS:
        for other in (tags.get(key) or "").split(";"):
            other = other.strip()
            if other and other != name and other not in names:
                names.append(other)
    return names


def apart(a: tuple, b: tuple) -> float:
    """How far apart two boxes (west, south, east, north) are, in degrees, along the further axis; 0 if they touch."""
    return max(b[0] - a[2], a[0] - b[2], b[1] - a[3], a[1] - b[3], 0)


def joined(a: dict, b: dict) -> dict:
    """Two records of one place as one. An outline says more than a point: where the middle
    is and how big the place is; two outlines are a group, shown whole."""
    if a["outline"] and b["outline"]:
        box = (min(a["box"][0], b["box"][0]), min(a["box"][1], b["box"][1]),
               max(a["box"][2], b["box"][2]), max(a["box"][3], b["box"][3]))
    else:
        box = b["box"] if b["outline"] else a["box"]
    return {"box": box, "outline": a["outline"] or b["outline"], "zoom": a["zoom"],
            "others": a["others"] + [o for o in b["others"] if o not in a["others"]]}


def metres(a: list, b: list) -> float:
    """Roughly how far apart two places are, in metres; close enough over a few kilometres."""
    return math.hypot((a[2] - b[2]) * 111320 * math.cos(math.radians(a[3])), (a[3] - b[3]) * 110540)


def route_segments(routes: str) -> list[tuple]:
    """The ferry routes the map draws (scripts/ferries.py), as straight segments."""
    segments = []
    with open(routes, encoding="utf-8") as f:
        for line in f:
            geometry = json.loads(line)["geometry"]
            lines = geometry["coordinates"] if geometry["type"] == "MultiLineString" else [geometry["coordinates"]]
            for coordinates in lines:
                segments += list(itertools.pairwise(coordinates))
    return segments


def off_route(place: list, segments: list[tuple]) -> float:
    """How far, in metres, a place is from the nearest ferry route, up to about 5 km."""
    lon, lat = place[2], place[3]
    scale = 111320 * math.cos(math.radians(lat))
    nearest = math.inf
    for (ax, ay), (bx, by) in segments:
        if min(ax, bx) - lon > 0.05 or lon - max(ax, bx) > 0.05 or min(ay, by) - lat > 0.05 or lat - max(ay, by) > 0.05:
            continue
        a = ((ax - lon) * scale, (ay - lat) * 110540)
        d = ((bx - ax) * scale, (by - ay) * 110540)
        length = d[0] ** 2 + d[1] ** 2
        t = 0 if not length else max(0, min(1, -(a[0] * d[0] + a[1] * d[1]) / length))
        nearest = min(nearest, math.hypot(a[0] + t * d[0], a[1] + t * d[1]))
    return nearest


def landings(terminals: list[list], segments: list[tuple]) -> list[list]:
    """One record for each landing the map's ferry routes reach.

    OpenStreetMap tags each berth and foot-passenger ramp as a ferry terminal, and some
    port berths too ("US Oil #1", "Pier 7-A"). A terminal more than ROUTE_REACH from any
    route is left out; terminals within LANDING of one another are one landing, named by
    the name whose words the most of them share, as "Swartz Bay Ferry Terminal" is by
    "Victoria (Swartz Bay) Berth 1" and the rest, and not by "Seaspan Ferries"."""
    served = [t for t in terminals if off_route(t, segments) <= ROUTE_REACH]
    groups: list[list[list]] = []
    for t in sorted(served, key=lambda t: (t[2], t[3])):
        near = [g for g in groups if any(metres(t, u) <= LANDING for u in g)]
        for g in near[1:]:
            near[0] += g
            groups.remove(g)
        if near:
            near[0].append(t)
        else:
            groups.append([t])

    def words(name: str) -> set[str]:
        return {w for w in re.findall(r"[a-z]+", name.casefold()) if w not in GENERIC_WORDS}

    def shared(name: str, group: list[list]) -> int:
        return sum(1 for u in group if words(name) & words(u[0]))

    kept = []
    for g in groups:
        # A route's or a corner's name ("Water Taxi Route & Harbor Ave SW") is a last resort.
        candidates = [t for t in g if not BERTH.search(t[0]) and not NOT_A_LANDING.search(t[0])]
        candidates = candidates or [t for t in g if not BERTH.search(t[0])]
        if not candidates:
            # Every name is a berth's, as at Anacortes: "Anacortes Slip 2" names the landing "Anacortes".
            candidates = [[BERTH_AND_AFTER.sub("", t[0]), *t[1:]] for t in g]
        kept.append(max(candidates, key=lambda t: (shared(t[0], g), -len(t[0]), t[0])))
    return kept


def osm(out: str, extracts: list[str], box: tuple[float, float, float, float], routes: str) -> None:
    import osmium

    west, south, east, north = box
    # Each place found so far, by kind and name: its box (a point is a box of no size),
    # whether the box is an outline, its zoom if it isn't, and its other names.
    found: dict[tuple[str, str], list[dict]] = {}

    def add(tags, kind: str, bounds: tuple, outline: bool, zoom: int) -> None:
        name = tags.get("name")
        lon, lat = (bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2
        if not name or not (west <= lon <= east and south <= lat <= north):
            return
        same = found.setdefault((kind, name), [])
        place = {"box": bounds, "outline": outline, "zoom": zoom, "others": other_names(tags, name)}
        # Fold in every record it is one place with, and then every record the grown place
        # is one with, so that a group comes out as one whatever order its islands are read in.
        merged = True
        while merged:
            merged = False
            for p in same:
                if apart(p["box"], place["box"]) >= (GROUP if place["outline"] and p["outline"] else SAME):
                    continue
                same.remove(p)
                place = joined(p, place)
                merged = True
                break
        same.append(place)

    wanted = osmium.filter.KeyFilter("place", "amenity")
    for extract in extracts:
        for o in osmium.FileProcessor(extract).with_areas(wanted).with_filter(wanted):
            tag = tag_of(o.tags)
            if not tag:
                continue
            kind = tag[1]
            if o.is_node():
                lon, lat = o.location.lon, o.location.lat
                add(o.tags, kind, (lon, lat, lon, lat), False, OSM_KINDS[tag])
            elif o.is_area():
                if kind not in FROM_OUTLINES:
                    continue
                lons, lats = [], []
                for ring in o.outer_rings():
                    for node in ring:
                        lons.append(node.lon)
                        lats.append(node.lat)
                if lons:
                    add(o.tags, kind, (min(lons), min(lats), max(lons), max(lats)), True, OSM_KINDS[tag])

    places = []
    for (kind, name), same in found.items():
        for p in same:
            w, s, e, n = p["box"]
            zoom = fit_zoom(w, s, e, n) if p["outline"] and kind in OUTLINED else p["zoom"]
            places.append([name, kind, rounded((w + e) / 2), rounded((s + n) / 2), zoom, p["others"]])
    terminals = [p for p in places if p[1] == "ferry_terminal"]
    places = [p for p in places if p[1] != "ferry_terminal"] + landings(terminals, route_segments(routes))
    write(out, OSM, places)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="list", required=True)
    g = sub.add_parser("gazetteers")
    g.add_argument("names")
    g.add_argument("out")
    o = sub.add_parser("osm")
    o.add_argument("out")
    o.add_argument("extracts", nargs="+")
    o.add_argument("--bbox", required=True)
    o.add_argument("--routes", required=True, help="the map's ferry routes, from scripts/ferries.py")
    args = parser.parse_args()
    if args.list == "gazetteers":
        gazetteers(args.names, args.out)
    else:
        osm(args.out, args.extracts, tuple(float(x) for x in args.bbox.split(",")), args.routes)


if __name__ == "__main__":
    main()
