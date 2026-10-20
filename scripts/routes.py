# /// script
# requires-python = ">=3.12"
# dependencies = ["shapely>=2"]
# ///
"""Shipping lanes and the other routes ships are told to keep to, from the two countries' charts (decisions/019).

  routes.py fetch DIR
      downloads the routeing areas over the coast region from NOAA's ENC Direct (US
      waters, public domain) and Fisheries and Oceans Canada's Vessel Traffic Routes
      (Open Government Licence – Canada) into DIR, one GeoJSON file each layer;
  routes.py build DIR routes.geojsons --bbox=W,S,E,N
      writes them as one GeoJSON feature a line, for tippecanoe: the areas, each with a
      `kind`, and points along each lane and two-way route for its direction arrows and
      its name.

NOAA's are used wherever NOAA charts, which includes Haro Strait and Boundary Pass, its
cells there being compiled from Canada's charts; Canada's are added only where NOAA has
nothing, such as the schemes off the Fraser River and Vancouver, cut away where they
overlap NOAA's. Taking each side of the border from its own country would have joined two
drawings of one route along the boundary, which runs down the middle of Haro Strait.
"""

import argparse
import json
import math
import urllib.parse
import urllib.request

from shapely.geometry import LineString, Point, box, mapping, shape
from shapely.ops import unary_union

# The coast region (Makefile), which every region's box lies within.
COAST = (-136.0, 36.0, -120.0, 54.8)
NOAA = "https://encdirect.noaa.gov/arcgis/rest/services/encdirect/enc_coastal/MapServer"
DFO = "https://egisp.dfo-mpo.gc.ca/arcgis/rest/services/open_data_donnees_ouvertes/vessel_traffic_routes_en/MapServer"
# Each layer fetched: its file, its service and layer, and the kind it gives each area by
# its S-57 object class (OBJL), as its layer may hold more than one.
LAYERS = {
    "noaa_lanes": (NOAA, 155), "noaa_recommended_lanes": (NOAA, 153), "noaa_two_way": (NOAA, 156),
    "noaa_separation_zones": (NOAA, 154), "noaa_precautionary": (NOAA, 152),
    "dfo_parts": (DFO, 4), "dfo_separation_zones": (DFO, 3), "dfo_other_zones": (DFO, 6),
}
KINDS = {
    148: "lane",             # traffic separation scheme lane part
    153: "lane",             # recommended traffic lane part
    152: "two_way",          # two-way route part
    150: "separation_zone",  # traffic separation zone
    96: "precautionary",     # precautionary area
}
# Arrows along a lane, and the gap between them, in metres; and the smallest piece of
# Canada's areas kept once NOAA's are cut away.
ARROW_SPACING = 6000
SMALLEST = 50_000
# The zooms the marks appear from: arrows, then the lanes' names.
ARROW_ZOOM = 9
NAME_ZOOM = 11


def fetch(out: str) -> None:
    west, south, east, north = COAST
    envelope = json.dumps({"xmin": west, "ymin": south, "xmax": east, "ymax": north, "spatialReference": {"wkid": 4326}})
    for name, (service, layer) in LAYERS.items():
        features, offset = [], 0
        while True:
            query = urllib.parse.urlencode({
                "geometry": envelope, "geometryType": "esriGeometryEnvelope", "inSR": 4326,
                "spatialRel": "esriSpatialRelIntersects", "outFields": "*", "outSR": 4326,
                "resultOffset": offset, "f": "geojson",
            })
            with urllib.request.urlopen(f"{service}/{layer}/query?{query}", timeout=120) as response:
                page = json.load(response)
            if "error" in page:
                raise SystemExit(f"{name}: {page['error']}")
            features += page["features"]
            if not page.get("exceededTransferLimit"):
                break
            offset = len(features)
        with open(f"{out}/{name}.geojson", "w", encoding="utf-8") as f:
            json.dump({"type": "FeatureCollection", "features": features}, f)
        print(f"{name}: {len(features)}")


def metres_per_degree(lat: float) -> tuple[float, float]:
    return 111320 * math.cos(math.radians(lat)), 110540


def read(path: str, area: object) -> list[tuple[str, int | None, object]]:
    """A layer's areas within `area`, as (kind, orientation, geometry); kinds this doesn't draw are left out."""
    with open(path, encoding="utf-8") as f:
        features = json.load(f)["features"]
    out = []
    for feature in features:
        p, g = feature["properties"], feature["geometry"]
        kind = KINDS.get(int(p["OBJL"])) if p.get("OBJL") not in (None, "") else None
        if not kind or not g:
            continue
        geometry = shape(g).buffer(0).intersection(area)
        if geometry.is_empty:
            continue
        orient = p.get("ORIENT")
        orient = round(float(orient)) % 360 if orient not in (None, "", " ") else None
        out.append((kind, orient, geometry))
    return out


def dissolved(areas: list[tuple[str, int | None, object]]) -> list[tuple[str, int | None, object]]:
    """Pieces of one area that the charts cut at their cells' edges, joined, so no line crosses a lane where a cell ends."""
    groups: dict[tuple[str, int | None], list] = {}
    for kind, orient, geometry in areas:
        groups.setdefault((kind, orient), []).append(geometry)
    out = []
    for (kind, orient), geometries in groups.items():
        union = unary_union(geometries)
        for polygon in getattr(union, "geoms", [union]):
            if polygon.geom_type == "Polygon" and not polygon.is_empty:
                out.append((kind, orient, polygon))
    return out


def compass(bearing: float) -> str:
    return ["North", "Northeast", "East", "Southeast", "South", "Southwest", "West", "Northwest"][round(bearing / 45) % 8]


def marks(kind: str, orient: int, polygon) -> list[dict]:
    """Points along a lane or a two-way route: an arrow every ARROW_SPACING, and between
    the middle two, its name. Each sits in the middle of the area across its direction."""
    c = polygon.representative_point()
    mx, my = metres_per_degree(c.y)
    dx, dy = math.sin(math.radians(orient)) / mx, math.cos(math.radians(orient)) / my
    along = [((x - c.x) * mx * math.sin(math.radians(orient)) + (y - c.y) * my * math.cos(math.radians(orient)))
             for x, y in polygon.exterior.coords]
    start, end = min(along), max(along)
    count = max(1, int((end - start) // ARROW_SPACING))
    gap = (end - start) / count
    # In metres, so that the line across, turned into degrees below, spans the whole area.
    width = max((polygon.bounds[2] - polygon.bounds[0]) * mx, (polygon.bounds[3] - polygon.bounds[1]) * my) * 2

    def middle(t: float) -> Point | None:
        """The middle of the area across its direction, `t` metres along it."""
        x, y = c.x + dx * t, c.y + dy * t
        # A line across the direction of travel, long enough to cross the whole area.
        across = LineString([(x - dy * my / mx * width, y + dx * mx / my * width), (x + dy * my / mx * width, y - dx * mx / my * width)])
        crossing = polygon.intersection(across)
        if crossing.is_empty:
            return None
        pieces = list(getattr(crossing, "geoms", [crossing]))
        piece = min(pieces, key=lambda p: p.distance(Point(x, y)))
        return piece.interpolate(0.5, normalized=True)

    # The arrow's glyph points east; a two-way route's points both ways.
    rotate = orient - 90
    out = []
    for i in range(count):
        point = middle(start + gap * (i + 0.5))
        if point:
            out.append({"geometry": point, "kind": "arrow", "glyph": "↔" if kind == "two_way" else "→", "rotate": rotate,
                        "minzoom": ARROW_ZOOM})
    # The name reads along the area, never upside down.
    turned = ((orient - 90 + 90) % 180) - 90
    name = "Two-way route" if kind == "two_way" else f"{compass(orient)}bound lane"
    point = middle(start + gap * (count // 2) if count > 1 else (start + end) / 2 + gap / 4)
    if point:
        out.append({"geometry": point, "kind": "name", "name": name.capitalize(), "rotate": turned, "minzoom": NAME_ZOOM})
    return out


def build(src: str, out: str, bbox: tuple[float, float, float, float]) -> None:
    region = box(*bbox)
    noaa = dissolved([a for name in LAYERS if name.startswith("noaa_") for a in read(f"{src}/{name}.geojson", region)])
    charted = unary_union([g for _, _, g in noaa])
    dfo = []
    for kind, orient, geometry in [a for name in LAYERS if name.startswith("dfo_") for a in read(f"{src}/{name}.geojson", region)]:
        rest = geometry.difference(charted)
        for polygon in getattr(rest, "geoms", [rest]):
            if polygon.geom_type != "Polygon" or polygon.is_empty:
                continue
            mx, my = metres_per_degree(polygon.centroid.y)
            # A sliver left along the edge of NOAA's area, or a scrap, is dropped.
            if polygon.area * mx * my >= SMALLEST and polygon.buffer(-200 / mx).area > 0:
                dfo.append((kind, orient, polygon))
    areas = [(k, o, g, "noaa") for k, o, g in noaa] + [(k, o, g, "dfo") for k, o, g in dissolved(dfo)]
    with open(out, "w", encoding="utf-8") as f:
        for kind, orient, polygon, source in areas:
            properties = {"kind": kind, "source": source}
            f.write(json.dumps({"type": "Feature", "properties": properties, "geometry": mapping(polygon),
                                "tippecanoe": {"layer": "areas"}}) + "\n")
            if kind in ("lane", "two_way") and orient is not None:
                for mark in marks(kind, orient, polygon):
                    geometry, minzoom = mark.pop("geometry"), mark.pop("minzoom")
                    f.write(json.dumps({"type": "Feature", "properties": mark, "geometry": mapping(geometry),
                                        "tippecanoe": {"layer": "marks", "minzoom": minzoom}}, ensure_ascii=False) + "\n")
    print(f"{out}: {sum(1 for a in areas if a[3] == 'noaa')} areas from NOAA, {sum(1 for a in areas if a[3] == 'dfo')} from Canada")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="step", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("dir")
    b = sub.add_parser("build")
    b.add_argument("dir")
    b.add_argument("out")
    b.add_argument("--bbox", required=True)
    args = parser.parse_args()
    if args.step == "fetch":
        fetch(args.dir)
    else:
        build(args.dir, args.out, tuple(float(x) for x in args.bbox.split(",")))


if __name__ == "__main__":
    main()
