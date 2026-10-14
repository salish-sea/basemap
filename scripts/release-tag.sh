#!/usr/bin/env bash
# Tags the commit being published with its version, as the animals register tags its
# releases, so each version on tiles.salishsea.io names the code that built it:
#   scripts/release-tag.sh 2026.10.1
# The commit must be clean and on origin's main. A tag that already points at it is
# fine, so a publish that failed partway can be run again; one that points elsewhere
# is refused, because a version is never reused (decisions/007).
set -euo pipefail
cd "$(dirname "$0")/.."

version="${1:?usage: scripts/release-tag.sh YYYY.MM.N}"
if [[ ! "$version" =~ ^[0-9]{4}\.[0-9]{2}\.[1-9][0-9]*$ ]]; then
  echo "usage: scripts/release-tag.sh YYYY.MM.N" >&2
  exit 2
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo "the checkout has uncommitted changes; commit and push them before publishing" >&2
  exit 1
fi
git fetch -q --tags origin main
if ! git merge-base --is-ancestor HEAD origin/main; then
  echo "HEAD is not on origin's main; push it before publishing" >&2
  exit 1
fi
head=$(git rev-parse HEAD)
if tagged=$(git rev-parse -q --verify "refs/tags/$version^{commit}"); then
  if [[ "$tagged" != "$head" ]]; then
    echo "$version is already the tag of another commit, $tagged; choose the next version" >&2
    exit 1
  fi
else
  git tag -a "$version" -m "Basemap $version"
fi
git push -q origin "refs/tags/$version"
