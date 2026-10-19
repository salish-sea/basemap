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
#   assets/basemaps-assets-<commit>/   the labels' fonts and the icons, uploaded once for
#                                      each commit of Protomaps' assets (decisions/010)
#   assets/fonts-<hash>/               the labels' fonts with the depth labels' serif
#                                      (decisions/017), named for their contents
#   assets/landmark-icons-<hash>/      the landmarks' sprite (decisions/015), named for its
#                                      contents
#   places/<list>-<hash>.json          the names the map labels, as lists a site can search
#                                      (decisions/018), named for their contents
#   images/<hash>/{z}/{x}/{y}.webp     the image tiles (decisions/014), under a name made
#                                      from their contents, so they too are shared; their
#                                      list, tiles.txt, goes up last, as the sign they're all there
#   <version>/style.json               the style, pointing at those archives and assets
#   <version>/viewer/index.html        the comparison page, for trying a build out
#   <version>/index.html               a page linking every file the version is made of
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
archives=(protomaps osm marine depth elevation landmarks)
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
make REGION="${REGION:-window}" archives images places
# The coast has a zoomed-out map, in two more archives (decisions/012).
for a in overview overview_elevation; do
  if [[ -f "$src/$a.pmtiles" ]]; then archives+=("$a"); fi
done

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

# The fonts and icons, once for each commit of Protomaps' assets. Their icons' licence
# goes up last, as the sign that the rest are there, and later publishes check for it
# rather than sending all 774 files again. (aws s3 sync would list and skip, but it
# ignores --no-overwrite, and the publisher may only add files that way.)
assets=$(node -e "import('./style/style.ts').then((m) => process.stdout.write(m.ASSETS_PATH))")
if [[ ! "$assets" =~ ^assets/basemaps-assets-[0-9a-f]{12}/$ ]]; then
  echo "could not read the assets' path from style/style.ts: '$assets'" >&2
  exit 1
fi
done_marker="${assets}sprites/LICENSE.md"
if ! aws s3api head-object --bucket "$bucket" --key "$done_marker" >/dev/null 2>&1; then
  aws s3 cp --only-show-errors --no-overwrite --recursive "build/$assets" "s3://$bucket/$assets" \
    --exclude sprites/LICENSE.md --cache-control "$year"
  aws s3 cp --only-show-errors --no-overwrite "build/$done_marker" "s3://$bucket/$done_marker" \
    --cache-control "$year"
fi

# The labels' fonts, Protomaps' and the depth labels' serif together (decisions/017), named
# for every file in them, by path and contents. Their licence goes up last, as the sign that
# the rest are there.
hash=$(node -e 'const fs = require("fs"), path = require("path"); const h = require("crypto").createHash("sha256");
  const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]);
  for (const f of walk("build/fonts").sort()) { h.update(path.relative("build/fonts", f)); h.update(fs.readFileSync(f)); }
  console.log(h.digest("hex").slice(0, 16));')
fonts="assets/fonts-$hash"
if aws s3api head-object --bucket "$bucket" --key "$fonts/OFL.txt" >/dev/null 2>&1; then
  echo "$fonts is already there"
else
  aws s3 cp --only-show-errors --no-overwrite --recursive build/fonts "s3://$bucket/$fonts" \
    --exclude OFL.txt --content-type application/x-protobuf --cache-control "$year"
  aws s3 cp --only-show-errors --no-overwrite build/fonts/OFL.txt "s3://$bucket/$fonts/OFL.txt" \
    --content-type text/plain --cache-control "$year"
fi

# The image tiles, named for the list and every tile in it, in the list's order.
hash=$(node -e 'const fs = require("fs"); const h = require("crypto").createHash("sha256");
  const [src] = process.argv.slice(1); const list = fs.readFileSync(`${src}/images.txt`, "utf8");
  h.update(list);
  for (const line of list.split("\n").filter(Boolean)) h.update(fs.readFileSync(`${src}/images/${line.replaceAll(" ", "/")}.webp`));
  console.log(h.digest("hex").slice(0, 16));' "$src")
images="images/$hash"
if aws s3api head-object --bucket "$bucket" --key "$images/tiles.txt" >/dev/null 2>&1; then
  echo "$images is already there"
else
  aws s3 cp --only-show-errors --no-overwrite --recursive "$src/images" "s3://$bucket/$images" \
    --exclude done --content-type image/webp --cache-control "$year"
  aws s3 cp --only-show-errors --no-overwrite "$src/images.txt" "s3://$bucket/$images/tiles.txt" \
    --content-type text/plain --cache-control "$year"
fi

# The landmarks' sprite, its two sizes' images and indexes, named for all four.
hash=$(cat build/sprites/landmarks.json build/sprites/landmarks.png build/sprites/landmarks@2x.json \
  build/sprites/landmarks@2x.png | node -e 'const h = require("crypto").createHash("sha256");
  process.stdin.on("data", (d) => h.update(d)).on("end", () => console.log(h.digest("hex").slice(0, 16)));')
icons="assets/landmark-icons-$hash"
for f in landmarks.png landmarks@2x.png landmarks@2x.json landmarks.json; do
  aws s3 cp --only-show-errors --no-overwrite "build/sprites/$f" "s3://$bucket/$icons/$f" --cache-control "$year"
done

# The names the map labels, as lists, each named for its contents.
places=()
for list in places-gazetteers places-osm; do
  hash=$(node -e 'const h = require("crypto").createHash("sha256");
    h.update(require("fs").readFileSync(process.argv[1])); console.log(h.digest("hex").slice(0, 16));' "$src/$list.json")
  key="places/$list-$hash.json"
  places+=("$list=https://tiles.salishsea.io/$key")
  aws s3 cp --only-show-errors --no-overwrite "$src/$list.json" "s3://$bucket/$key" \
    --content-type 'application/json; charset=utf-8' --cache-control "$year"
done

rm -rf "$out" && mkdir -p "$out"
node style/emit.ts "https://tiles.salishsea.io/archives/" "${urls[@]}" \
  "images=https://tiles.salishsea.io/$images/{z}/{x}/{y}.webp" \
  "landmark-icons=https://tiles.salishsea.io/$icons/landmarks" \
  "glyphs=https://tiles.salishsea.io/$fonts/" "${places[@]}" > "$out/style.json"
archives_json=$(node -e 'console.log(JSON.stringify(Object.fromEntries(process.argv.slice(1).map((a) => a.split(/=(.*)/s).slice(0, 2)))))' "${urls[@]}")
VITE_TILES_ARCHIVES="$archives_json" VITE_LANDMARK_ICONS="https://tiles.salishsea.io/$icons/landmarks" \
  VITE_GLYPHS="https://tiles.salishsea.io/$fonts/" \
  pnpm exec vite build viewer --outDir "../$out/viewer" --emptyOutDir --logLevel warn
aws s3 cp --only-show-errors --no-overwrite --recursive "$out/viewer" "s3://$bucket/$version/viewer" \
  --cache-control "$year"
# The index page, linking every file the version is made of, since the ones named for
# their contents can't be guessed from the version.
node scripts/version_index.ts "$version" "$out/style.json" "$src" > "$out/index.html"
aws s3 cp --only-show-errors --no-overwrite "$out/index.html" "s3://$bucket/$version/index.html" \
  --content-type 'text/html; charset=utf-8' --cache-control "$year"
# Last: its presence marks the version as published.
aws s3 cp --only-show-errors --no-overwrite "$out/style.json" "s3://$bucket/$version/style.json" \
  --content-type application/json --cache-control "$year"

echo "https://tiles.salishsea.io/$version/index.html"
echo "next, from a checkout: scripts/release.sh $version"
