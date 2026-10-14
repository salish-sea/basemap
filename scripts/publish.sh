#!/usr/bin/env bash
# Publishes one region's build as a version of tiles.salishsea.io:
#   scripts/publish.sh 2026.10.1               the test window, build/window
#   REGION=coast scripts/publish.sh 2026.10.2  the whole range, build/coast
# Versions are CalVer, as the animals register's releases are: the year, the month, and
# a count within the month. Run from a checkout, it first tags the commit with the
# version (scripts/release-tag.sh); on a build machine, fly/run.sh has already done so.
# A published version is never changed: style.json is uploaded last, as
# the sign that a version is complete, and the script refuses a version that has one, so
# a page that names a version always gets the same map. A publish that failed partway can
# be finished by running it again with the same build.
#
# Uploads, under https://tiles.salishsea.io/<version>/:
#   *.pmtiles          the archives
#   style.json         the style, pointing at those archives
#   viewer/index.html  the comparison page, for trying a build out
#
# Needs the BasemapTiles stack deployed (infra/) and credentials for Orcasound's AWS
# account. AWS_PROFILE defaults to orcasound; on a build machine, use a profile for the
# stack's basemap-publisher user, which can add files but not change or delete them:
#   AWS_PROFILE=basemap scripts/publish.sh 2026.10.1
set -euo pipefail
cd "$(dirname "$0")/.."

version="${1:-}"
if [[ ! "$version" =~ ^[0-9]{4}\.[0-9]{2}\.[1-9][0-9]*$ ]]; then
  echo "usage: scripts/publish.sh YYYY.MM.N" >&2
  exit 2
fi
# A key in the environment, as on the build machine, is used as it is; otherwise a profile.
if [[ -z "${AWS_ACCESS_KEY_ID:-}" ]]; then
  export AWS_PROFILE="${AWS_PROFILE:-orcasound}"
fi
archives=(protomaps osm marine depth elevation)
src="build/${REGION:-window}"
out="build/publish/$version"
for a in "${archives[@]}"; do
  [[ -f "$src/$a.pmtiles" ]] || { echo "missing $src/$a.pmtiles; run make REGION=${REGION:-window}" >&2; exit 1; }
done

bucket=$(aws cloudformation describe-stacks --region us-west-2 --stack-name BasemapTiles \
  --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" --output text 2>/dev/null || true)
if [[ -z "$bucket" || "$bucket" == None ]]; then
  echo "no BasemapTiles stack in us-west-2; deploy infra/ first" >&2
  exit 1
fi
if head=$(aws s3api head-object --bucket "$bucket" --key "$version/style.json" 2>&1); then
  echo "version $version is already published; choose another" >&2
  exit 1
elif [[ "$head" != *"Not Found"* && "$head" != *"404"* ]]; then
  echo "could not check whether $version is published: $head" >&2
  exit 1
fi

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  scripts/release-tag.sh "$version"
fi

rm -rf "$out" && mkdir -p "$out"
node style/emit.ts "https://tiles.salishsea.io/$version/" > "$out/style.json"
VITE_TILES_BASE=../ pnpm exec vite build viewer --outDir "../$out/viewer" --emptyOutDir --logLevel warn

# Every file lives under a path that never changes, so it may be cached for a year.
# --no-overwrite skips a file that is already there, which lets a rerun finish a publish
# that failed partway; the basemap-publisher user can't overwrite one anyway.
year='public, max-age=31536000, immutable'
for a in "${archives[@]}"; do
  aws s3 cp --only-show-errors --no-overwrite "$src/$a.pmtiles" "s3://$bucket/$version/$a.pmtiles" \
    --content-type application/octet-stream --cache-control "$year"
done
aws s3 cp --only-show-errors --no-overwrite --recursive "$out/viewer" "s3://$bucket/$version/viewer" \
  --cache-control "$year"
# Last: its presence marks the version as published.
aws s3 cp --only-show-errors --no-overwrite "$out/style.json" "s3://$bucket/$version/style.json" \
  --content-type application/json --cache-control "$year"

echo "https://tiles.salishsea.io/$version/style.json"
echo "https://tiles.salishsea.io/$version/viewer/index.html"
