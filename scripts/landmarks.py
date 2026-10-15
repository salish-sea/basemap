# /// script
# requires-python = ">=3.12"
# dependencies = ["osmium>=4"]
# ///
"""Landmarks a person on the water or the shore steers by, from OpenStreetMap (decisions/015).

Writes one GeoJSON point a line, each with a `kind`, a `name` if it has a usable one, and
the zoom it first appears at, as tippecanoe's `minzoom`:

- lighthouses: a light the charts call major, or a `man_made=lighthouse` with a name of
  its own (`name`), as the lighthouses people know have; the hundreds of minor lights on
  piles and rocks, named only for the chart (`seamark:name`), are left out;
- towers: radio and television masts and towers that the charts mark as landmarks, or
  that are 100 m or taller. A charted mast or tower with no tags to say what it carries
  counts when masts named for a station's call sign, such as KAFE-FM, stand within MERGE
  metres of it, as on Mount Constitution;
- landmarks: anything else the charts mark as a landmark (`seamark:type=landmark`), such
  as a chimney, a dome or a spire, which charts include because it is conspicuous from
  the water. Cranes are left out: they come and go. So is a charted landmark that carries a
  light, which is a minor light's tower: British Columbia's lights, imported from the US
  light list, are tagged that way.

Points within MERGE metres of one another are one landmark, so a broadcast site with seven
masts is drawn once; it takes the kind, name and height of the most prominent of them.
"""

import argparse
import json
import math
import re

import osmium

MERGE = 500
TALL = 100
KINDS = ("lighthouse", "tower", "landmark")
# The zoom each kind first appears at, unnamed and named.
MINZOOM = {"lighthouse": (11, 9), "tower": (10, 10), "landmark": (12, 11)}
# Names that are a record's label rather than a place's: "vts 3669705", "TV", "(KIRO) 710KHz", "Marker".
NOT_A_NAME = re.compile(r"^(vts\b|tv$|marker$|\(|\d)", re.IGNORECASE)
# A broadcast station's call sign, as GNIS names the towers it imported: "KAFE-FM (Bellingham)".
CALL_SIGN = re.compile(r"^[KCW][A-Z]{2,3}(-(AM|FM|TV|LP|DT))?\b")


def height(tags) -> float:
    match = re.match(r"\s*([0-9.]+)", tags.get("height", "") or "")
    try:
        return float(match.group(1)) if match else 0.0
    except ValueError:
        return 0.0


def classify(tags) -> str | None:
    man_made = tags.get("man_made")
    seamark = tags.get("seamark:type")
    # Most of an extract is neither; the checks below read every tag, so they wait for this.
    if man_made not in ("lighthouse", "mast", "tower", "communications_tower") and seamark not in ("light_major", "landmark"):
        return None
    if seamark == "light_major" or (man_made == "lighthouse" and tags.get("name")):
        return "lighthouse"
    if man_made == "lighthouse":
        return None
    communication = man_made == "communications_tower" or tags.get("tower:type") in ("communication", "radio", "broadcast") \
        or any(tag.k.startswith("communication:") for tag in tags)
    if man_made in ("mast", "tower", "communications_tower") and communication and (seamark == "landmark" or height(tags) >= TALL):
        return "tower"
    lit = any(tag.k.startswith("seamark:light:") for tag in tags)
    if seamark == "landmark" and man_made != "crane" and not lit:
        return "landmark"
    return None


def name_of(tags) -> str | None:
    name = (tags.get("name") or tags.get("seamark:name") or "").strip()
    # "KIRO-TV (Seattle)" is KIRO-TV; the town is on the map.
    name = re.sub(r"\s*\([^)]*\)$", "", name)
    return name if name and not NOT_A_NAME.search(name) else None


class Collect(osmium.SimpleHandler):
    def __init__(self, box: tuple[float, float, float, float]):
        super().__init__()
        self.box = box
        self.found: dict[tuple[str, int], dict] = {}
        # Masts named for a station, which say what an unlabelled charted tower near them is.
        self.stations: dict[tuple[str, int], tuple[float, float]] = {}

    def add(self, kind_of: str, osm_id: int, tags, lon: float, lat: float) -> None:
        west, south, east, north = self.box
        if not (west <= lon <= east and south <= lat <= north):
            return
        if tags.get("man_made") in ("mast", "tower") and CALL_SIGN.match(tags.get("name") or ""):
            self.stations[(kind_of, osm_id)] = (lon, lat)
        kind = classify(tags)
        if kind:
            # An extract's neighbours overlap at the border, so a point is kept once.
            self.found[(kind_of, osm_id)] = {
                "kind": kind, "name": name_of(tags), "height": height(tags), "lon": lon, "lat": lat,
                "structure": tags.get("man_made") in ("mast", "tower"),
            }

    @staticmethod
    def wanted(tags) -> bool:
        return (tags.get("man_made") in ("mast", "tower") and "name" in tags) or classify(tags) is not None

    def node(self, n) -> None:
        if self.wanted(n.tags):
            self.add("n", n.id, n.tags, n.location.lon, n.location.lat)

    def way(self, w) -> None:
        if self.wanted(w.tags):
            try:
                points = [(node.lon, node.lat) for node in w.nodes]
            except osmium.InvalidLocationError:
                return
            self.add("w", w.id, w.tags, sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points))


def metres(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot((a[0] - b[0]) * 111_320 * math.cos(math.radians(a[1])), (a[1] - b[1]) * 111_320)


def prominence(point: dict) -> tuple:
    """Which of several points close together stands for them: the first kind, a named one, the tallest."""
    return (KINDS.index(point["kind"]), point["name"] is None, -point["height"])


def merge(points: list[dict]) -> list[dict]:
    """Points within MERGE metres of a more prominent one are folded into it."""
    kept: list[dict] = []
    for point in sorted(points, key=prominence):
        metres_per_degree = 111_320 * math.cos(math.radians(point["lat"]))
        near = next((k for k in kept if math.hypot((k["lon"] - point["lon"]) * metres_per_degree,
                                                    (k["lat"] - point["lat"]) * 111_320) < MERGE), None)
        if near:
            near["height"] = max(near["height"], point["height"])
            near["name"] = near["name"] or point["name"]
        else:
            kept.append(dict(point))
    return kept


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out")
    parser.add_argument("extracts", nargs="+", help="OpenStreetMap extracts, .osm.pbf")
    parser.add_argument("--bbox", required=True, help="west,south,east,north")
    args = parser.parse_args()
    box = tuple(float(v) for v in args.bbox.split(","))

    found: dict = {}
    stations: dict = {}
    for extract in args.extracts:
        collect = Collect(box)
        collect.apply_file(extract, locations=True)
        found.update(collect.found)
        stations.update(collect.stations)
    for point in found.values():
        if point["kind"] == "landmark" and point["structure"] and any(
                metres((point["lon"], point["lat"]), s) < MERGE for s in stations.values()):
            point["kind"] = "tower"
    landmarks = merge(list(found.values()))
    with open(args.out, "w") as out:
        for point in landmarks:
            unnamed, named = MINZOOM[point["kind"]]
            properties = {"kind": point["kind"], **({"name": point["name"]} if point["name"] else {})}
            if point["height"]:
                properties["height"] = round(point["height"])
            out.write(json.dumps({
                "type": "Feature", "properties": properties,
                "tippecanoe": {"minzoom": named if point["name"] else unnamed},
                "geometry": {"type": "Point", "coordinates": [round(point["lon"], 6), round(point["lat"], 6)]},
            }) + "\n")
    counts = {kind: sum(p["kind"] == kind for p in landmarks) for kind in KINDS}
    print(f"{len(landmarks)} landmarks: " + ", ".join(f"{c} {k}s" for k, c in counts.items()))


if __name__ == "__main__":
    main()
