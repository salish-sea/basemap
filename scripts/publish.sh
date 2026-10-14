#!/usr/bin/env bash
# Publishes build/window as one version of tiles.salishsea.io:
#   scripts/publish.sh 2026-10-13
# The version names the build, by date, with a letter for a second build that day
# (2026-10-13b). A published version is never changed: the script refuses one that
# already exists, so a page that names a version always gets the same map.
#
# Uploads, under https://tiles.salishsea.io/<version>/:
#   *.pmtiles          the archives
#   style.json         the style, pointing at those archives
#   viewer/index.html  the comparison page, for trying a build out
#
# Needs the BasemapTiles stack deployed (infra/) and credentials for Orcasound's AWS
# account; AWS_PROFILE defaults to orcasound.
set -euo pipefail
cd "$(dirname "$0")/.."

version="${1:-}"
if [[ ! "$version" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}[a-z]?$ ]]; then
  echo "usage: scripts/publish.sh YYYY-MM-DD[letter]" >&2
  exit 2
fi
export AWS_PROFILE="${AWS_PROFILE:-orcasound}"
archives=(protomaps osm marine depth elevation)
src=build/window
out="build/publish/$version"
for a in "${archives[@]}"; do
  [[ -f "$src/$a.pmtiles" ]] || { echo "missing $src/$a.pmtiles; run make window" >&2; exit 1; }
done

bucket=$(aws cloudformation describe-stacks --region us-east-1 --stack-name BasemapTiles \
  --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" --output text)
if [[ -n "$(aws s3 ls "s3://$bucket/$version/" 2>/dev/null)" ]]; then
  echo "version $version is already published; choose another" >&2
  exit 1
fi

rm -rf "$out" && mkdir -p "$out"
node style/emit.ts "https://tiles.salishsea.io/$version/" > "$out/style.json"
VITE_TILES_BASE=../ pnpm exec vite build viewer --outDir "../$out/viewer" --emptyOutDir --logLevel warn

# Every file lives under a path that never changes, so it may be cached for a year.
year='public, max-age=31536000, immutable'
for a in "${archives[@]}"; do
  aws s3 cp --only-show-errors "$src/$a.pmtiles" "s3://$bucket/$version/$a.pmtiles" \
    --content-type application/octet-stream --cache-control "$year"
done
aws s3 cp --only-show-errors "$out/style.json" "s3://$bucket/$version/style.json" \
  --content-type application/json --cache-control "$year"
aws s3 cp --only-show-errors --recursive "$out/viewer" "s3://$bucket/$version/viewer" \
  --cache-control "$year"

echo "https://tiles.salishsea.io/$version/style.json"
echo "https://tiles.salishsea.io/$version/viewer/index.html"
