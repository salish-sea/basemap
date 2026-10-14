# /// script
# requires-python = ">=3.12"
# dependencies = ["shapely>=2", "pyproj>=3.6"]
# ///
"""Draw each ferry channel once.

Where several routes share a channel, such as the Washington State Ferries routes from
Anacortes through the San Juan Islands, OpenStreetMap maps each route separately, a few
hundred metres apart. Drawn dashed, side by side, they look like rope. This writes two
layers from the same routes:

  ferries       one line per channel, for the zooms where routes that close together
                can't be told apart. Routes are taken longest first; each later route
                keeps only its parts outside the earlier ones, joined back to the line
                it leaves from.
  ferry_routes  every route as mapped, with its name, for close zooms and for labels;
                the style decides from which zoom each is drawn.

Input is GeoJSONSeq with a `name` and `network` per route; output is two GeoJSONSeq
files; the channel lines carry tippecanoe's per-feature maximum zoom.
"""

import argparse
import json
import math

from pyproj import Transformer
from shapely import LineString, MultiLineString, Point, unary_union
from shapely.geometry import mapping, shape
from shapely.ops import linemerge, nearest_points, transform

TO_MERCATOR = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
TO_DEGREES = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform


def read(path: str) -> list[dict]:
    features = []
    with open(path) as f:
        for line in f:
            line = line.strip("\x1e \n")
            if line:
                feature = json.loads(line)
                if feature.get("geometry"):
                    features.append(feature)
    return features


def lines(geom) -> list[LineString]:
    if geom.is_empty:
        return []
    if isinstance(geom, LineString):
        return [geom]
    if hasattr(geom, "geoms"):
        return [g for part in geom.geoms for g in lines(part)]
    return []


def write(path: str, rows: list[tuple[object, dict, int | None]]) -> None:
    with open(path, "w") as f:
        for geom, props, maxzoom in rows:
            feature = {
                "type": "Feature",
                "properties": {k: v for k, v in props.items() if v is not None},
                "geometry": mapping(transform(TO_DEGREES, geom)),
            }
            if maxzoom is not None:
                feature["tippecanoe"] = {"maxzoom": maxzoom}
            f.write(json.dumps(feature) + "\n")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("routes", help="GeoJSONSeq of ferry routes")
    p.add_argument("channels_out", help="GeoJSONSeq, one line per channel")
    p.add_argument("routes_out", help="GeoJSONSeq, every route")
    p.add_argument("--within", type=float, default=300, help="metres on the ground within which routes share a channel")
    p.add_argument("--split-zoom", type=int, default=13, help="first zoom that draws every route separately")
    args = p.parse_args()

    routes = []
    for feature in read(args.routes):
        geom = transform(TO_MERCATOR, shape(feature["geometry"]))
        merged = linemerge(geom) if isinstance(geom, MultiLineString) else geom
        props = {k: feature["properties"].get(k) for k in ("name", "network")}
        routes.append((merged, props))
    routes.sort(key=lambda r: r[0].length, reverse=True)

    channels: list[tuple[object, dict, int | None]] = []
    drawn = None  # everything drawn so far, as lines
    corridor = None  # the area within `within` of it
    for geom, props in routes:
        # Web Mercator stretches distances by 1/cos(latitude); scale the tolerance to match.
        lat = TO_DEGREES(geom.centroid.x, geom.centroid.y)[1]
        within = args.within / math.cos(math.radians(lat))
        # A route that only crosses another's channel, like the Guemes Island ferry
        # across Guemes Channel, doesn't share it, so it is drawn whole.
        shared = corridor is not None and geom.intersection(corridor).length > 3 * within
        outside = geom.difference(corridor) if shared else geom
        for piece in lines(outside):
            # Drop slivers left where a route leaves a shared channel, never a whole route.
            if shared and piece.length < within:
                continue
            if drawn is not None:
                # Join each end that stopped at the edge of a shared channel back to it.
                coords = list(piece.coords)
                for end in (0, -1):
                    tip = Point(coords[end])
                    nearest = nearest_points(drawn, tip)[0]
                    if nearest.distance(tip) <= within * 1.05:
                        if end == 0:
                            coords.insert(0, (nearest.x, nearest.y))
                        else:
                            coords.append((nearest.x, nearest.y))
                piece = LineString(coords)
            channels.append((piece, {"network": props["network"]}, args.split_zoom - 1))
            drawn = piece if drawn is None else unary_union([drawn, piece])
        corridor = None if drawn is None else drawn.buffer(within)

    write(args.channels_out, channels)
    write(args.routes_out, [(geom, props, None) for geom, props in routes])
    print(f"{len(routes)} routes; {len(channels)} channel lines")


if __name__ == "__main__":
    main()
