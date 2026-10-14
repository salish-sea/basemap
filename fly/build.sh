#!/usr/bin/env bash
# Runs on the build machine (fly/Dockerfile): builds a region and, given a version,
# publishes it.
#   fly/build.sh coast               build only
#   fly/build.sh coast 2026-10-20    build, then publish as that version
# Source grids are cached on the volume at /data, so only the first build downloads
# them (about 12 GB). Publishing uses the basemap-publisher user's key, which the Fly app
# holds as the secrets AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.
set -euo pipefail
region="${1:?usage: fly/build.sh REGION [VERSION]}"
version="${2:-}"

mkdir -p /data/cache /data/build
ln -sfn /data/cache /app/cache
ln -sfn /data/build /app/build
cd /app

echo "building $region with $(nproc) CPUs; $(df -h /data | awk 'NR==2 {print $4}') free on /data"
time make REGION="$region"
du -sh "build/$region"/*.pmtiles

if [[ -n "$version" ]]; then
  REGION="$region" AWS_DEFAULT_REGION=us-west-2 scripts/publish.sh "$version"
fi
