#!/usr/bin/env bash
# Tags the commit being published with its version, as the animals register tags its
# releases, so each version on tiles.salishsea.io names the code that built it:
#   scripts/release-tag.sh 2026.10.1
# The commit must be clean and on origin's main. A tag that already points at it is
# fine, so a publish that failed partway can be run again. A tag on another commit is
# moved here if that version never got as far as being published, as when a build
# failed and its fix is a new commit; once a version is published, its tag is fixed
# (decisions/007).
set -euo pipefail
cd "$(dirname "$0")/.."

version="${1:?usage: scripts/release-tag.sh YYYY.MM.N}"
if [[ ! "$version" =~ ^[0-9]{4}\.(0[1-9]|1[0-2])\.[1-9][0-9]*$ ]]; then
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
    # style.json is uploaded last, so a version without one was never published.
    status=$(curl -s -o /dev/null -w '%{http_code}' "https://tiles.salishsea.io/$version/style.json")
    if [[ "$status" == 200 ]]; then
      echo "$version is published, from commit $tagged; choose the next version" >&2
      exit 1
    elif [[ "$status" != 403 && "$status" != 404 ]]; then
      echo "could not check whether $version is published (HTTP $status)" >&2
      exit 1
    fi
    echo "moving the tag $version from $tagged, which was never published, to $head" >&2
    git tag -f -a "$version" -m "Basemap $version"
    git push -q -f origin "refs/tags/$version"
    exit 0
  fi
else
  git tag -a "$version" -m "Basemap $version"
fi
git push -q origin "refs/tags/$version"
