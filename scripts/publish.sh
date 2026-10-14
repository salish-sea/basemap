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
# Uploads:
#   archives/<archive>-<hash>.pmtiles  each archive, named for its contents, so one
#                                      that hasn't changed since an earlier version is
#                                      already there and is shared, not uploaded again
#   <version>/style.json               the style, pointing at those archives
#   <version>/viewer/index.html        the comparison page, for trying a build out
#
# Needs the BasemapTiles stack deployed (infra/) and credentials for Orcasound's AWS
# account. AWS_PROFILE defaults to orcasound; on a build machine, use a profile for the
# stack's basemap-publisher user, which can add files but not change or delete them:
#   AWS_PROFILE=basemap scripts/publish.sh 2026.10.1
set -euo pipefail
cd "$(dirname "$0")/.."

version="${1:-}"
if [[ ! "$version" =~ ^[0-9]{4}\.(0[1-9]|1[0-2])\.[1-9][0-9]*$ ]]; then
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

# Brings the archives up to date with this commit, so the tag names the code that built
# them; on a build machine, fly/build.sh has just run it, and it does nothing.
make REGION="${REGION:-window}"

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  scripts/release-tag.sh "$version"
fi

# Every file lives under a path that never changes, so it may be cached for a year.
# --no-overwrite skips a file that is already there: an archive an earlier version
# shares, or one a publish that failed partway got as far as uploading. The
# basemap-publisher user can't overwrite a file anyway.
year='public, max-age=31536000, immutable'
urls=()
for a in "${archives[@]}"; do
  # The first 16 hex digits of its SHA-256, which no two different archives will share.
  hash=$(node -e 'const h = require("crypto").createHash("sha256");
    require("fs").createReadStream(process.argv[1]).on("data", (d) => h.update(d))
      .on("end", () => console.log(h.digest("hex").slice(0, 16)));' "$src/$a.pmtiles")
  key="archives/$a-$hash.pmtiles"
  urls+=("$a=https://tiles.salishsea.io/$key")
  # --no-overwrite alone would still send the whole file before S3 refused it.
  if aws s3api head-object --bucket "$bucket" --key "$key" >/dev/null 2>&1; then
    echo "$key is already there"
    continue
  fi
  aws s3 cp --only-show-errors --no-overwrite "$src/$a.pmtiles" "s3://$bucket/$key" \
    --content-type application/octet-stream --cache-control "$year"
done

rm -rf "$out" && mkdir -p "$out"
node style/emit.ts "https://tiles.salishsea.io/archives/" "${urls[@]}" > "$out/style.json"
archives_json=$(node -e 'console.log(JSON.stringify(Object.fromEntries(process.argv.slice(1).map((a) => a.split(/=(.*)/s).slice(0, 2)))))' "${urls[@]}")
VITE_TILES_ARCHIVES="$archives_json" pnpm exec vite build viewer --outDir "../$out/viewer" --emptyOutDir --logLevel warn
aws s3 cp --only-show-errors --no-overwrite --recursive "$out/viewer" "s3://$bucket/$version/viewer" \
  --cache-control "$year"
# Last: its presence marks the version as published.
aws s3 cp --only-show-errors --no-overwrite "$out/style.json" "s3://$bucket/$version/style.json" \
  --content-type application/json --cache-control "$year"

echo "https://tiles.salishsea.io/$version/style.json"
echo "https://tiles.salishsea.io/$version/viewer/index.html"
