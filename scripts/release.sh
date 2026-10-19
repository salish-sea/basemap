#!/usr/bin/env bash
# Announces a published version, from a checkout, once its publish has finished:
#   scripts/release.sh 2026.10.14
# Makes the version's GitHub release on its tag, linking the version's index page, and
# points the README at the version (scripts/readme-version.ts), which leaves README.md to
# commit. It runs after publishing, not when the tag is pushed, because a build that fails
# skips its version number, and a release made then could name a version that never got
# published (decisions/007). Run again, it rewrites the release's notes.
set -euo pipefail
cd "$(dirname "$0")/.."

version="${1:-}"
if [[ ! "$version" =~ ^[0-9]{4}\.(0[1-9]|1[0-2])\.[1-9][0-9]*$ ]]; then
  echo "usage: scripts/release.sh YYYY.MM.N" >&2
  exit 2
fi
base="https://tiles.salishsea.io/$version"
for file in style.json index.html; do
  status=$(curl -s -o /dev/null -w '%{http_code}' "$base/$file")
  if [[ "$status" != 200 ]]; then
    echo "$base/$file answered $status; has $version finished publishing?" >&2
    exit 1
  fi
done

git fetch -q --tags origin
previous=$(git describe --tags --abbrev=0 "$version^" 2>/dev/null || true)
notes="Every file of this version, its image tiles, place lists and archives among them: $base/index.html

- Style: $base/style.json
- Comparison page, beside Esri's map: $base/viewer/index.html"
if [[ -n "$previous" ]]; then
  notes+="

Changes since $previous: https://github.com/salish-sea/basemap/compare/$previous...$version"
fi

if gh release view "$version" >/dev/null 2>&1; then
  gh release edit "$version" --notes "$notes"
else
  gh release create "$version" --verify-tag --title "Basemap $version" --notes "$notes"
fi
node scripts/readme-version.ts "$version"
echo "commit README.md, which now names $version"
