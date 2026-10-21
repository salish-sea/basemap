#!/usr/bin/env bash
# Starts a build in Docker on this machine, from this checkout (decision 021):
#   builder/run.sh coast               build only
#   builder/run.sh coast 2026.10.2     build and publish as that version, after tagging
#                                      this commit with it (scripts/release-tag.sh)
# Builds the image from builder/Dockerfile and runs it in the background with
# $BASEMAP_DATA (~/basemap-data unless set) at /data, which keeps the source grids between
# builds and holds the working files and archives. Publishing reads the basemap-publisher
# user's key from ~/.config/basemap/publisher.env, as AWS_ACCESS_KEY_ID=… and
# AWS_SECRET_ACCESS_KEY=… lines. Follow it with: docker logs -f basemap-build
set -euo pipefail
# Absolute, and resolved from where run.sh was started: Docker reads a bare name as a volume's.
data="$(realpath -m "${BASEMAP_DATA:-$HOME/basemap-data}")"
cd "$(dirname "$0")/.."
key="$HOME/.config/basemap/publisher.env"
env_file=()
# Checked before anything is tagged: a second build can't start while one runs.
if [[ "$(docker inspect -f '{{.State.Running}}' basemap-build 2>/dev/null)" == true ]]; then
  echo "a build is already running; follow it with: docker logs -f basemap-build" >&2
  exit 1
fi
if [[ -n "${2:-}" ]]; then
  if [[ ! -r "$key" ]]; then
    echo "publishing needs the basemap-publisher user's key in $key" >&2
    exit 1
  fi
  scripts/release-tag.sh "$2"
  env_file=(--env-file "$key")
fi
mkdir -p "$data"
docker build -f builder/Dockerfile -t salishsea-basemap-build .
# The last build's container is kept until the next starts, so its log can still be read.
if docker inspect basemap-build >/dev/null 2>&1; then docker rm basemap-build >/dev/null; fi
docker run --detach --name basemap-build --volume "$data:/data" --env DATA_OWNER="$(id -u):$(id -g)" \
  "${env_file[@]}" salishsea-basemap-build "$@"
echo "follow it with: docker logs -f basemap-build"
