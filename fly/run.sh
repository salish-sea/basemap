#!/usr/bin/env bash
# Starts a build on a Fly machine, from this checkout (decision 008):
#   fly/run.sh coast               build only
#   fly/run.sh coast 2026.10.2     build and publish as that version, after tagging
#                                  this commit with it (scripts/release-tag.sh)
# Builds the image from fly/Dockerfile, runs it on an 8-CPU machine (or FLY_VM_SIZE) with the app's volume
# at /data, and removes the machine when the build ends; the volume, with the cached
# source grids, stays. Follow it with: fly logs -a salishsea-basemap-build
set -euo pipefail
cd "$(dirname "$0")/.."
app=salishsea-basemap-build
if [[ -n "${2:-}" ]]; then scripts/release-tag.sh "$2"; fi
volume=$(fly volumes list -a "$app" --json | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["id"])')
fly machine run . "$@" --dockerfile fly/Dockerfile -a "$app" --region sjc \
  --vm-size "${FLY_VM_SIZE:-performance-8x}" --volume "$volume:/data" --restart no --rm --detach
