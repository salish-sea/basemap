# /// script
# requires-python = ">=3.12"
# dependencies = ["osmium>=4", "shapely>=2"]
# ///
"""Where parks' names go, and nature reserves' outlines on the land, from OpenStreetMap (decisions/026).

  parks.py points.geojsons sea.geojsons labels.geojsons reserves.geojsons extract.osm.pbf ... --bbox=W,S,E,N

points.geojsons holds Protomaps' points of interest of the kinds park, national_park and
nature_reserve, with their names, kinds and first zooms. Protomaps puts each at any point
inside its park, which for Deception Pass State Park is in its north, where few people
go. This keeps Protomaps' choice of which parks are named, of what kind and from which
zoom, and moves the name of each park at least WIDE_PARK metres across to its
headquarters, office, ranger station or visitor centre, if one lies on its land. Every
other park keeps Protomaps' point. The middle of a park's land was tried too, and lost: in
a park that is a whole island, it is where the island's own name sits, which wins.

It also writes the outlines of the nature reserves among them that are named as parks,
such as Deception Pass State Park, less the sea in sea.geojsons, so that they can be
tinted as parks are without tinting the water they reach over.
"""

import argparse
import json
import math
import re

import osmium
from shapely.geometry import Point, mapping, shape
from shapely.ops import unary_union
from shapely.strtree import STRtree

PARK_TAGS = {"leisure": ("park", "nature_reserve"), "boundary": ("national_park", "protected_area"), "landuse": ("park",)}
# A park's headquarters, by its name or its tags. One whose name includes the park's comes
# first, as "Deception Pass State Park Headquarters" does; then a ranger station or office;
# then a visitor centre.
OFFICE_NAME = re.compile(r"\b(headquarters|office|ranger station|visitor('?s)? cent(er|re)|welcome (station|cent(er|re))|registration station)\b", re.I)
# A nature reserve is tinted as a park only when it is named as one, as most state and
# provincial parks are, and not a wildlife area or a state forest such as Capitol State
# Forest, which is timberland (decisions/026).
PARK_NAME = re.compile(r"\bpark\b", re.I)
# Only a park at least this many metres across has its name moved. In a smaller one any
# point is near everything in it, and a name moved to its headquarters can land beside the
# park's own landmark, whose icon takes its place: Lime Kiln Point State Park's ranger
# station is 70 m from its lighthouse.
WIDE_PARK = 1000
# How far, in degrees, a headquarters may lie outside its park's outline, as a building on
# its edge does; and a Protomaps point outside its outline, which Protomaps' tiles round.
NEAR = 0.0005


def office_rank(tags: dict[str, str], park: str) -> int | None:
    """How good a park's headquarters this is, best first, or None if it isn't one."""
    name = tags.get("name", "")
    if name.lower() == park.lower():
        return None  # the park itself, mapped as a point
    if name and park.lower() in name.lower() and OFFICE_NAME.search(name):
        return 0
    if tags.get("amenity") == "ranger_station" or tags.get("information") == "office":
        return 1
    if tags.get("information") == "visitor_centre" or OFFICE_NAME.search(name):
        return 2
    return None


def across(geometry) -> float:
    """The longer side of a geometry's bounds, in metres."""
    west, south, east, north = geometry.bounds
    return max((east - west) * math.cos(math.radians((south + north) / 2)), north - south) * 111_320


def is_office(tags: dict[str, str]) -> bool:
    return (tags.get("amenity") == "ranger_station" or tags.get("information") in ("office", "visitor_centre")
            or bool(OFFICE_NAME.search(tags.get("name", ""))))


class Collect(osmium.SimpleHandler):
    def __init__(self, names: set[str]):
        super().__init__()
        self.names = names
        # Each park's outlines by name, with the OpenStreetMap object each came from.
        self.outlines: dict[str, list] = {}
        self.offices: list[tuple[dict, Point]] = []

    def node(self, n) -> None:
        tags = dict(n.tags)
        if is_office(tags):
            self.offices.append((tags, Point(n.location.lon, n.location.lat)))

    def area(self, a) -> None:
        tags = dict(a.tags)
        park = tags.get("name") in self.names and any(tags.get(k) in v for k, v in PARK_TAGS.items())
        if not (park or is_office(tags)):
            return
        polygons = []
        for ring in a.outer_rings():
            coords = [(node.lon, node.lat) for node in ring]
            holes = [[(node.lon, node.lat) for node in inner] for inner in a.inner_rings(ring)]
            if len(coords) >= 4:
                polygons.append(shape({"type": "Polygon", "coordinates": [coords, *[h for h in holes if len(h) >= 4]]}).buffer(0))
        if not polygons:
            return
        outline = unary_union(polygons)
        if park:
            self.outlines.setdefault(tags["name"], []).append((a.id, outline))
        if is_office(tags):
            self.offices.append((tags, outline.representative_point()))


def read_lines(path: str):
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.lstrip("\x1e").strip()
            if line:
                yield json.loads(line)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("points")
    parser.add_argument("sea")
    parser.add_argument("labels")
    parser.add_argument("reserves")
    parser.add_argument("extracts", nargs="+")
    parser.add_argument("--bbox", required=True, help="west,south,east,north")
    args = parser.parse_args()
    west, south, east, north = (float(v) for v in args.bbox.split(","))

    # Protomaps' tiles hold a point once in each tile whose edge it lies near.
    points, seen = [], set()
    for f in read_lines(args.points):
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"]
        key = (p.get("name"), round(lon, 5), round(lat, 5))
        if p.get("name") and key not in seen and west <= lon <= east and south <= lat <= north:
            seen.add(key)
            points.append({"name": p["name"], "kind": p["kind"], "min_zoom": int(p["min_zoom"]), "at": Point(lon, lat)})

    collect = Collect({p["name"] for p in points})
    wanted = osmium.filter.KeyFilter("leisure", "boundary", "landuse", "amenity", "tourism", "office")
    for extract in args.extracts:
        collect.apply_file(extract, locations=True, filters=[wanted])
    offices = STRtree([at for _, at in collect.offices])
    sea_shapes = [shape(f["geometry"]) for f in read_lines(args.sea)]
    sea = STRtree(sea_shapes)

    def land(outline):
        """The outline less the sea, which is empty for a reserve wholly at sea."""
        water = [sea_shapes[i] for i in sea.query(outline, predicate="intersects")]
        return outline.difference(unary_union(water)) if water else outline

    placed = {"headquarters": 0, "protomaps": 0}
    reserves: dict[int, tuple[str, object]] = {}
    with open(args.labels, "w", encoding="utf-8") as out:
        for p in points:
            containing = [(oid, o) for oid, o in collect.outlines.get(p["name"], []) if o.buffer(NEAR).contains(p["at"])]
            at, how = p["at"], "protomaps"
            if containing:
                oid, outline = min(containing, key=lambda c: c[1].area)
                on_land = land(outline)
                # On the park's land, or on its edge, as a building at its gate is; not on a
                # pier out in the part of the outline that is sea.
                near = on_land.buffer(NEAR)
                ranked = [(rank, office_at) for i in offices.query(near, predicate="contains")
                          for tags, office_at in [collect.offices[i]]
                          if (rank := office_rank(tags, p["name"])) is not None]
                if ranked and not on_land.is_empty and across(on_land) >= WIDE_PARK:
                    at, how = min(ranked, key=lambda r: r[0])[1], "headquarters"
                if p["kind"] == "nature_reserve" and PARK_NAME.search(p["name"]) and not on_land.is_empty:
                    reserves[oid] = (p["name"], on_land)
            placed[how] += 1
            out.write(json.dumps({
                "type": "Feature",
                "properties": {"name": p["name"], "kind": p["kind"], "min_zoom": p["min_zoom"], "placed": how},
                "geometry": {"type": "Point", "coordinates": [round(at.x, 6), round(at.y, 6)]},
                "tippecanoe": {"minzoom": min(p["min_zoom"], 14)},
            }, ensure_ascii=False) + "\n")
    with open(args.reserves, "w", encoding="utf-8") as out:
        for name, outline in reserves.values():
            out.write(json.dumps({"type": "Feature", "properties": {"name": name}, "geometry": mapping(outline)}, ensure_ascii=False) + "\n")
    print(f"{args.labels}: {len(points)} parks' names, {placed['headquarters']} moved to a headquarters, {placed['protomaps']} where Protomaps put them")
    print(f"{args.reserves}: {len(reserves)} outlines on the land of nature reserves named as parks")


if __name__ == "__main__":
    main()
