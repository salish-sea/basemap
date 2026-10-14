#!/usr/bin/env bash
# Cuts depth bands from an elevation grid in horizontal strips, into one GeoPackage layer
# named `contour`, as `gdal_contour -p` would in one go:
#   scripts/contour_bands.sh dem.tif bands.gpkg LEVEL...
# gdal_contour keeps every polygon in memory until it finishes, which for the whole coast
# is more than the build machine has. gdal_contour's polygons cover whole cells, out to
# the edge of the strip, so strips that don't overlap meet exactly: each band's area
# comes out the same as from one pass over the test window.
set -euo pipefail
dem="$1"; out="$2"; shift 2
strip=${STRIP:-4096}
read -r width height < <(gdalinfo "$dem" | sed -n 's/^Size is \([0-9]*\), \([0-9]*\)$/\1 \2/p')
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
rm -f "$out"
for ((y = 0; y < height; y += strip)); do
  rows=$(( y + strip > height ? height - y : strip ))
  gdal_translate -q -of VRT -srcwin 0 "$y" "$width" "$rows" "$dem" "$tmp/strip.vrt"
  rm -f "$tmp/strip.gpkg"
  gdal_contour -q -p -amin elev_min -amax elev_max -fl "$@" "$tmp/strip.vrt" "$tmp/strip.gpkg"
  ogr2ogr -append -nln contour "$out" "$tmp/strip.gpkg" contour
done
