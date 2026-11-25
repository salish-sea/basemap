#!/usr/bin/env bash
# Runs on the build machine (builder/Dockerfile): builds a region's archives and image tiles
# and, given a version, publishes them.
#   builder/build.sh coast               build only
#   builder/build.sh coast 2026.10.2     build, then publish as that version
# Source grids are cached in /data, so only the first build downloads them (about 15 GB).
# Publishing uses the basemap-publisher user's key, which builder/run.sh passes in as
# AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.
set -euo pipefail
region="${1:?usage: builder/build.sh REGION [VERSION]}"
version="${2:-}"

# The container runs as root; builder/run.sh says whose /data is, so it can hand back
# what the build wrote, even when the build fails.
if [[ -n "${DATA_OWNER:-}" ]]; then trap 'chown -R "$DATA_OWNER" /data' EXIT; fi
# The temporary files start afresh, owned by root: Chromium, as root, has no WebGL with a
# temporary directory someone else owns, and the image tiles then never draw.
rm -rf /data/tmp
mkdir -p /data/cache /data/build /data/tmp
# tippecanoe's sorting files, and GDAL's and SQLite's, are as big as the inputs, so
# they go in /data rather than the container's own filesystem.
export TMPDIR=/data/tmp
ln -sfn /data/cache /app/cache
ln -sfn /data/build /app/build
cd /app

# Each build keeps its log, and how long each of make's steps took, in build/<region>/logs/,
# named for when it started, so a build's times can be read after the next has run and
# compared with earlier ones. builder/run.sh says which commit it is.
logs="build/$region/logs"
mkdir -p "$logs"
stamp="$(date -u +%Y-%m-%dT%H%M%SZ)"
exec > >(tee -a "$logs/$stamp.log") 2>&1
export BUILD_TIMING="$PWD/$logs/$stamp.timing.jsonl"
echo "building $region${version:+ as $version} from ${BUILD_COMMIT:-an unknown commit} with $(nproc) CPUs and" \
  "${JOBS:-6} jobs; $(df -h /data | awk 'NR==2 {print $4}') free on /data"
# Most of the archives' steps use one core, so make runs several at once. Not one for each
# core: each step that reads OpenStreetMap's extracts holds about 5 GB, and at the start
# several of those run beside the grids' warps.
time make -j"${JOBS:-6}" SHELL=builder/timed-shell.py REGION="$region" archives images places water
du -sh "build/$region"/*.pmtiles

if [[ -n "$version" ]]; then
  REGION="$region" AWS_DEFAULT_REGION=us-west-2 scripts/publish.sh "$version"
fi
