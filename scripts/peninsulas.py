# /// script
# requires-python = ">=3.12"
# dependencies = ["osmium>=4", "shapely>=2"]
# ///
"""Names of peninsulas from OpenStreetMap, for labels the map draws itself (decisions/018).

  peninsulas.py peninsulas.geojsons extract.osm.pbf ... --bbox=W,S,E,N

Protomaps keeps a peninsula only as a point of interest of the kind `peninsula`, from zoom
12 whatever its size, and its style never draws it. This writes every named peninsula,
`natural=peninsula`, as one GeoJSON point a line: at the point inside its outline furthest
from its edge, or at its node if it has no outline, with the zoom its name first appears
at, as `min_zoom`. A big peninsula is named earlier than a small one, as islands are: the
Olympic Peninsula from LABEL_ZOOMS[0], Key Peninsula from 7, Miller Peninsula from 8.
"""

import argparse
import json
import math

import osmium
from shapely.geometry import Point, Polygon
from shapely.ops import polylabel, unary_union

# A name appears two zooms before its peninsula fits one tile, as an islet's does, and not
# before LABEL_ZOOMS[0]; a peninsula drawn only as a point appears at LABEL_ZOOMS[1], as
# Protomaps gives every peninsula.
LABEL_ZOOMS = (6, 12)


def fit_zoom(west: float, south: float, east: float, north: float) -> int:
    """The zoom at which a box's longer side spans one 512-pixel tile, as in scripts/islets.py."""
    y = lambda lat: math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    span = max((east - west) / 360, (y(north) - y(south)) / (2 * math.pi))
    return LABEL_ZOOMS[1] + 2 if span <= 0 else math.floor(math.log2(1 / span))


class Collect(osmium.SimpleHandler):
    def __init__(self, box: tuple[float, float, float, float]):
        super().__init__()
        self.box = box
        # Each peninsula's point and the zoom it fits at, None for a node.
        self.found: list[dict] = []
        # Each outline by name, so that a node inside one of the same name, as Quimper
        # Peninsula's is, is known to be that peninsula's.
        self.outlines: dict[str, list] = {}

    def inside(self, lon: float, lat: float) -> bool:
        west, south, east, north = self.box
        return west <= lon <= east and south <= lat <= north

    def node(self, n) -> None:
        if n.tags.get("natural") == "peninsula" and n.tags.get("name") and self.inside(n.location.lon, n.location.lat):
            self.found.append({"name": n.tags["name"], "lon": n.location.lon, "lat": n.location.lat, "fits": None})

    def area(self, a) -> None:
        if a.tags.get("natural") != "peninsula" or not a.tags.get("name"):
            return
        polygons = []
        for ring in a.outer_rings():
            coords = [(node.lon, node.lat) for node in ring]
            holes = [[(node.lon, node.lat) for node in inner] for inner in a.inner_rings(ring)]
            if len(coords) >= 4:
                polygons.append(Polygon(coords, [h for h in holes if len(h) >= 4]).buffer(0))
        if not polygons:
            return
        outline = unary_union(polygons)
        self.outlines.setdefault(a.tags["name"], []).append(outline)
        largest = max(getattr(outline, "geoms", [outline]), key=lambda g: g.area)
        point = polylabel(largest, tolerance=0.00002)
        if self.inside(point.x, point.y):
            self.found.append({"name": a.tags["name"], "lon": point.x, "lat": point.y, "fits": fit_zoom(*outline.bounds)})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("out")
    parser.add_argument("extracts", nargs="+")
    parser.add_argument("--bbox", required=True, help="west,south,east,north")
    args = parser.parse_args()
    collect = Collect(tuple(float(v) for v in args.bbox.split(",")))
    wanted = osmium.filter.KeyFilter("natural")
    for extract in args.extracts:
        collect.apply_file(extract, locations=True, filters=[wanted])
    written = 0
    # The extracts overlap at their borders, so one peninsula can be read twice.
    seen = set()
    with open(args.out, "w", encoding="utf-8") as f:
        for p in sorted(collect.found, key=lambda p: (p["name"], p["lon"], p["lat"])):
            key = (p["name"], round(p["lon"], 6), round(p["lat"], 6))
            if key in seen:
                continue
            if p["fits"] is None and any(o.contains(Point(p["lon"], p["lat"])) for o in collect.outlines.get(p["name"], [])):
                continue
            seen.add(key)
            minzoom = LABEL_ZOOMS[1] if p["fits"] is None else max(LABEL_ZOOMS[0], min(LABEL_ZOOMS[1], p["fits"] - 2))
            f.write(json.dumps({
                "type": "Feature", "properties": {"name": p["name"], "min_zoom": minzoom},
                "geometry": {"type": "Point", "coordinates": [round(p["lon"], 6), round(p["lat"], 6)]},
                "tippecanoe": {"minzoom": minzoom},
            }, ensure_ascii=False) + "\n")
            written += 1
    print(f"{args.out}: {written} peninsulas")


if __name__ == "__main__":
    main()
