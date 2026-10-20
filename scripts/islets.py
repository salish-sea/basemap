# /// script
# requires-python = ">=3.12"
# dependencies = ["osmium>=4", "shapely>=2"]
# ///
"""Names of islets and small islands from OpenStreetMap, for labels the map draws itself (decisions/018).

  islets.py islets.geojsons extract.osm.pbf ... --bbox=W,S,E,N

Protomaps' tiles keep an islet only when it is also tagged `natural=coastline`, as a point
of the kind `coastline`. Many are tagged only `place=islet` or `place=island`, such as
Ben Ure Island and Deception Island at Deception Pass, and never reach the tiles. This
writes every named islet, and every named island small enough that Protomaps leaves it to
its points, as one GeoJSON point a line: at the point inside its outline furthest from the
shore, or at its node if it has no outline, with the zoom its name first appears at, as
`min_zoom`. Larger islands are labelled by Protomaps, as before.
"""

import argparse
import json
import math

import osmium
from shapely.geometry import Polygon
from shapely.ops import polylabel, unary_union

# An island whose longer side fits one 512-pixel tile from this zoom is labelled here; a
# bigger one is Protomaps'. Hat Island fits at 13.
SMALLEST_PROTOMAPS_ISLAND = 12
# A name appears two zooms before its island fits one tile, when it spans about a quarter of
# a tile, and not before LABEL_ZOOMS[0]; an islet drawn only as a point appears at
# LABEL_ZOOMS[1]. Ben Ure Island, at Deception Pass, appears at 14, as Protomaps' Strawberry Island does.
LABEL_ZOOMS = (11, 15)
# The last zoom the landmarks' archive, which carries these, has tiles for (the Makefile's -z).
TILES_UNTIL = 14
# Two records of one name this close, in degrees, are one place, as an islet drawn as a
# point and as an outline.
SAME = 0.005


def fit_zoom(west: float, south: float, east: float, north: float) -> int:
    """The zoom at which a box's longer side spans one 512-pixel tile, as in scripts/places.py."""
    y = lambda lat: math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    span = max((east - west) / 360, (y(north) - y(south)) / (2 * math.pi))
    return LABEL_ZOOMS[1] + 1 if span <= 0 else math.floor(math.log2(1 / span))


class Collect(osmium.SimpleHandler):
    def __init__(self, box: tuple[float, float, float, float]):
        super().__init__()
        self.box = box
        # Each place by name: its point, and the zoom it fits at if it has an outline.
        self.found: dict[str, list[dict]] = {}

    def inside(self, lon: float, lat: float) -> bool:
        west, south, east, north = self.box
        return west <= lon <= east and south <= lat <= north

    def add(self, name: str, lon: float, lat: float, fits: int | None) -> None:
        same = self.found.setdefault(name, [])
        for p in same:
            if abs(p["lon"] - lon) < SAME and abs(p["lat"] - lat) < SAME:
                # An outline says where the middle is and how big the place is; a point doesn't.
                if fits is not None and p["fits"] is None:
                    p.update(lon=lon, lat=lat, fits=fits)
                return
        same.append({"lon": lon, "lat": lat, "fits": fits})

    def node(self, n) -> None:
        if n.tags.get("place") in ("islet", "island") and n.tags.get("name") and self.inside(n.location.lon, n.location.lat):
            self.add(n.tags["name"], n.location.lon, n.location.lat, None)

    def area(self, a) -> None:
        if a.tags.get("place") not in ("islet", "island") or not a.tags.get("name"):
            return
        polygons = []
        for ring in a.outer_rings():
            coords = [(node.lon, node.lat) for node in ring]
            # A lake on the island is a hole, so the name isn't placed in it.
            holes = [[(node.lon, node.lat) for node in inner] for inner in a.inner_rings(ring)]
            if len(coords) >= 4:
                polygons.append(Polygon(coords, [h for h in holes if len(h) >= 4]).buffer(0))
        if not polygons:
            return
        outline = unary_union(polygons)
        largest = max(getattr(outline, "geoms", [outline]), key=lambda g: g.area)
        point = polylabel(largest, tolerance=0.00002)
        if self.inside(point.x, point.y):
            self.add(a.tags["name"], point.x, point.y, fit_zoom(*outline.bounds))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("out")
    parser.add_argument("extracts", nargs="+")
    parser.add_argument("--bbox", required=True, help="west,south,east,north")
    args = parser.parse_args()
    collect = Collect(tuple(float(v) for v in args.bbox.split(",")))
    wanted = osmium.filter.KeyFilter("place")
    for extract in args.extracts:
        collect.apply_file(extract, locations=True, filters=[wanted])
    written = 0
    with open(args.out, "w", encoding="utf-8") as f:
        for name, places in sorted(collect.found.items()):
            for p in places:
                if p["fits"] is not None and p["fits"] < SMALLEST_PROTOMAPS_ISLAND:
                    continue
                minzoom = LABEL_ZOOMS[1] if p["fits"] is None else max(LABEL_ZOOMS[0], min(LABEL_ZOOMS[1], p["fits"] - 2))
                # The archive's tiles stop at TILES_UNTIL and are enlarged past it, so a name
                # appearing later is in those tiles, and the style holds it back by `min_zoom`.
                f.write(json.dumps({
                    "type": "Feature", "properties": {"name": name, "min_zoom": minzoom},
                    "geometry": {"type": "Point", "coordinates": [round(p["lon"], 6), round(p["lat"], 6)]},
                    "tippecanoe": {"minzoom": min(minzoom, TILES_UNTIL)},
                }, ensure_ascii=False) + "\n")
                written += 1
    print(f"{args.out}: {written} islets and small islands")


if __name__ == "__main__":
    main()
