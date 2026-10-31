#!/usr/bin/env bash
# Cuts depth bands from an elevation grid in horizontal strips, into one GeoPackage layer
# named `contour`, as `gdal_contour -p` would in one go:
#   scripts/contour_bands.sh dem.tif bands.gpkg LEVEL...
# gdal_contour keeps every polygon in memory until it finishes, which for the whole coast
# is more than the build machine has. gdal_contour's polygons cover whole cells, out to
# the edge of the strip, so strips that don't overlap meet exactly: each band's area
# comes out the same as from one pass over the test window.
# The strips are cut side by side, JOBS at a time (as many as the machine has cores unless
# set), and appended in order, so the layer is the same as from one strip at a time. Each
# keeps a small cache of the grid's blocks rather than GDAL's default, 5% of the machine's
# memory, which is most of what a strip uses: about 1.6 GB a strip over the coast, against
# 0.3 GB at this size, in the same time.
set -euo pipefail
dem="$1"; out="$2"; shift 2
strip=${STRIP:-4096}
jobs=${JOBS:-$(getconf _NPROCESSORS_ONLN)}
read -r width height < <(gdalinfo "$dem" | sed -n 's/^Size is \([0-9]*\), \([0-9]*\)$/\1 \2/p')
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
export GDAL_CACHEMAX=${GDAL_CACHEMAX:-256} dem width tmp levels="$*"
cut_strip() {
  # The levels are words, such as MIN and -2000, so they are split on purpose.
  # shellcheck disable=SC2086
  gdal_translate -q -of VRT -srcwin 0 "$1" "$width" "$2" "$dem" "$tmp/$1.vrt" \
    && gdal_contour -q -p -amin elev_min -amax elev_max -fl $levels "$tmp/$1.vrt" "$tmp/$1.gpkg"
}
export -f cut_strip
for ((y = 0; y < height; y += strip)); do
  echo "$y $(( y + strip > height ? height - y : strip ))"
done | xargs -P "$jobs" -L 1 bash -c 'cut_strip "$@"' _
rm -f "$out"
for ((y = 0; y < height; y += strip)); do
  ogr2ogr -append -nln contour "$out" "$tmp/$y.gpkg" contour
done
