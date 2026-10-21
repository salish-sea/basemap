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

mkdir -p /data/cache /data/build /data/tmp
# tippecanoe's sorting files, and GDAL's and SQLite's, are as big as the inputs, so
# they go in /data rather than the container's own filesystem.
export TMPDIR=/data/tmp
ln -sfn /data/cache /app/cache
ln -sfn /data/build /app/build
cd /app

echo "building $region with $(nproc) CPUs; $(df -h /data | awk 'NR==2 {print $4}') free on /data"
time make REGION="$region" archives images places
du -sh "build/$region"/*.pmtiles

if [[ -n "$version" ]]; then
  REGION="$region" AWS_DEFAULT_REGION=us-west-2 scripts/publish.sh "$version"
fi
