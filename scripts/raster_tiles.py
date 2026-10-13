# /// script
# requires-python = ">=3.12"
# dependencies = ["rasterio>=1.4", "numpy>=2", "pillow>=11", "pmtiles>=3.4", "mercantile>=1.2"]
# ///
"""Cut an elevation grid into a PMTiles archive of 512-pixel WebP tiles.

Two kinds of archive, from the same grid:

  terrarium  Elevations encoded in red, green and blue (Mapzen's Terrarium encoding),
             lossless. MapLibre shades these itself (a `hillshade` layer) and can
             colour depth from them (`color-relief`).
  shade      Shading computed here and baked in: black where the slope faces away from
             the light, white where it faces it, transparent where it is flat. Drawn
             full strength; the style sets how much of it shows (decision 073).

Every zoom level is resampled from the grid itself, not from the level above, so the
shading at a low zoom is computed from a smoothed surface rather than averaged from
sharper shading.
"""

import argparse
import io
import math
import multiprocessing as mp

import mercantile
import numpy as np
import rasterio
from affine import Affine
from PIL import Image
from pmtiles.tile import Compression, TileType, zxy_to_tileid
from pmtiles.writer import Writer
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT

TILE = 512
BUFFER = 2  # pixels read beyond each edge, so shading has neighbours at the seams

_src: rasterio.DatasetReader | None = None
_native: float = 0.0
_args: argparse.Namespace | None = None


def _init(path: str, args: argparse.Namespace) -> None:
    global _src, _native, _args
    _args = args
    _src = rasterio.open(path)
    # The source's pixel size in Web Mercator metres at its middle latitude, roughly.
    lat = (_src.bounds.bottom + _src.bounds.top) / 2
    _native = abs(_src.transform.a) * 111320 / math.cos(math.radians(lat))


def _read(tile: mercantile.Tile) -> tuple[np.ndarray, float]:
    """The tile's elevations, BUFFER pixels wider on each side, and the pixel size in metres."""
    b = mercantile.xy_bounds(tile)
    res = (b.right - b.left) / TILE
    left, top = b.left - BUFFER * res, b.top + BUFFER * res
    size = TILE + 2 * BUFFER
    # Average down to zooms coarser than the grid; between its pixels, interpolate.
    resampling = Resampling.average if res > _native * 1.5 else Resampling.bilinear
    with WarpedVRT(
        _src, crs="EPSG:3857", transform=Affine(res, 0, left, 0, -res, top),
        width=size, height=size, resampling=resampling,
    ) as vrt:
        data = vrt.read(1, masked=True)
    return np.ma.filled(data.astype("float32"), np.nan), res


def _terrarium(elev: np.ndarray, precision: float) -> Image.Image:
    # Rounding to a coarser step than the encoding's 1/256 m compresses far better,
    # and a 30 m grid holds nothing finer than a fraction of a metre anyway.
    elev = np.round(np.nan_to_num(elev, nan=0.0) / precision) * precision
    v = elev + 32768.0
    r = np.floor(v / 256.0)
    g = np.floor(v - r * 256.0)
    b = np.floor((v - np.floor(v)) * 256.0)
    rgb = np.stack([r, g, b], axis=-1).clip(0, 255).astype("uint8")
    return Image.fromarray(rgb, "RGB")


def _shade(elev: np.ndarray, res: float, lat: float, exaggeration: float) -> Image.Image:
    # Web Mercator stretches distances by 1/cos(latitude); undo that so slopes are true.
    ground = res * math.cos(math.radians(lat))
    z = np.nan_to_num(elev, nan=0.0) * exaggeration
    dzdy, dzdx = np.gradient(z, ground)  # rows run north to south
    slope = np.arctan(np.hypot(dzdx, dzdy))
    aspect = np.arctan2(-dzdx, dzdy)
    azimuth, altitude = math.radians(315.0), math.radians(45.0)
    lit = (math.sin(altitude) * np.cos(slope)
           + math.cos(altitude) * np.sin(slope) * np.cos(azimuth - math.pi / 2 - aspect))
    flat = math.sin(altitude)
    shadow = np.clip((flat - lit) / flat, 0, 1)
    highlight = np.clip((lit - flat) / (1 - flat), 0, 1)
    tone = np.where(lit < flat, 0, 255).astype("uint8")
    alpha = (np.maximum(shadow, highlight) * 255).astype("uint8")
    alpha[np.isnan(elev)] = 0
    rgba = np.stack([tone, tone, tone, alpha], axis=-1)
    return Image.fromarray(rgba, "RGBA")


def _render(t: tuple[int, int, int]) -> tuple[int, bytes | None]:
    tile = mercantile.Tile(t[1], t[2], t[0])
    tile_id = zxy_to_tileid(tile.z, tile.x, tile.y)
    elev, res = _read(tile)
    inner = elev[BUFFER:-BUFFER, BUFFER:-BUFFER]
    if np.isnan(inner).all():
        return tile_id, None
    buf = io.BytesIO()
    if _args.kind == "terrarium":
        _terrarium(inner, _args.precision).save(buf, "WEBP", lossless=True, method=4)
    else:
        lat = mercantile.ul(tile.x, tile.y + 0.5, tile.z).lat
        img = _shade(elev, res, lat, _args.exaggeration)
        img.crop((BUFFER, BUFFER, BUFFER + TILE, BUFFER + TILE)).save(buf, "WEBP", quality=_args.quality, method=4)
    return tile_id, buf.getvalue()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("kind", choices=["terrarium", "shade"])
    p.add_argument("source", help="elevation grid in metres, negative below sea level")
    p.add_argument("output", help="PMTiles archive to write")
    p.add_argument("--bbox", required=True, help="west,south,east,north in degrees")
    p.add_argument("--minzoom", type=int, default=0)
    p.add_argument("--maxzoom", type=int, required=True)
    p.add_argument("--exaggeration", type=float, default=3.0, help="vertical exaggeration for shading")
    p.add_argument("--precision", type=float, default=0.25, help="metres to round elevations to")
    p.add_argument("--quality", type=int, default=80, help="WebP quality for shading")
    args = p.parse_args()

    west, south, east, north = map(float, args.bbox.split(","))
    tiles = sorted(
        ((t.z, t.x, t.y) for z in range(args.minzoom, args.maxzoom + 1)
         for t in mercantile.tiles(west, south, east, north, z)),
        key=lambda t: zxy_to_tileid(*t),
    )

    written = 0
    with open(args.output, "wb") as f, mp.Pool(initializer=_init, initargs=(args.source, args)) as pool:
        writer = Writer(f)
        for tile_id, data in pool.imap(_render, tiles, chunksize=8):
            if data is not None:
                writer.write_tile(tile_id, data)
                written += 1
        writer.finalize(
            {
                "tile_type": TileType.WEBP,
                "tile_compression": Compression.NONE,
                "min_zoom": args.minzoom,
                "max_zoom": args.maxzoom,
                "min_lon_e7": int(west * 1e7), "min_lat_e7": int(south * 1e7),
                "max_lon_e7": int(east * 1e7), "max_lat_e7": int(north * 1e7),
                "center_zoom": args.minzoom,
                "center_lon_e7": int((west + east) / 2 * 1e7),
                "center_lat_e7": int((south + north) / 2 * 1e7),
            },
            {
                "name": f"salish-sea-{args.kind}",
                "encoding": "terrarium" if args.kind == "terrarium" else None,
                "tileSize": TILE,
                "attribution": "NOAA NCEI; Natural Resources Canada",
            },
        )
    print(f"{args.output}: {written} of {len(tiles)} tiles")


if __name__ == "__main__":
    main()
