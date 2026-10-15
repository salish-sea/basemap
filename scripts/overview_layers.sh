#!/usr/bin/env bash
# Splits the zoomed-out map's depth bands and land at the region's edge (decisions/012):
#   scripts/overview_layers.sh BANDS.gpkg OUTDIR REGION_BBOX OVERVIEW_BBOX
# BANDS.gpkg is scripts/contour_bands.sh's polygons of the coarse grid; the boxes are
# west,south,east,north. It writes three files of GeoJSON lines into OUTDIR:
#   sea-outside.geojsons   depth bands outside the region, which the map draws at every zoom
#   land-outside.geojsons  land outside the region, likewise
#   sea-inside.geojsons    depth bands inside it, which the map draws only below the zoom where the
#                          region's own, finer bands start
# Nothing outside the region overlaps the region's own layers. What lies outside is cut
# as four strips around it, which meet without overlapping, because -clipdst keeps only
# what lies inside a box.
set -euo pipefail
bands="$1"; out="$2"
IFS=, read -r west south east north <<<"$3"
IFS=, read -r ow os oe on <<<"$4"
sea="SELECT CAST(-elev_max AS INTEGER) AS depth, geom FROM contour WHERE elev_max <= 0"
land="SELECT geom FROM contour WHERE elev_min >= 0"
strips=("$ow $os $west $on" "$east $os $oe $on" "$west $os $east $south" "$west $north $east $on")
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

clip() { # clip SQL BOX OUTPUT
  # shellcheck disable=SC2086 # the box is four words on purpose
  ogr2ogr -f GeoJSONSeq "$3" "$bands" -dialect SQLite -sql "$1" -clipdst $2
}

clip "$sea" "$west $south $east $north" "$tmp/sea-inside.geojsons"
for name in sea land; do
  sql=$sea; [[ $name == land ]] && sql=$land
  for i in "${!strips[@]}"; do
    clip "$sql" "${strips[$i]}" "$tmp/$name-$i"
  done
  cat "$tmp/$name"-[0-3] > "$tmp/$name-outside.geojsons"
done
mkdir -p "$out"
mv "$tmp/sea-inside.geojsons" "$tmp/sea-outside.geojsons" "$tmp/land-outside.geojsons" "$out/"
