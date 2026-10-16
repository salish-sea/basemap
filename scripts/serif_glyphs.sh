#!/usr/bin/env bash
# Builds the depth labels' glyphs (decisions/017) from Noto Serif, into style/fonts/:
#   scripts/serif_glyphs.sh
# Only the first block of 256 characters is kept: the labels are digits, a space and "m".
# The font is fetched from the Noto project at one commit and checked against its hash.
# Needs build_pbf_glyphs (cargo install build_pbf_glyphs). The output is checked in, so a
# build doesn't need it; run this again only to change the font.
set -euo pipefail
commit=28b15b4b43b7bed62b5cf6e6b0b5ff5846270535
sha256=19e72cd8d595fae5bd74a5206f5d938512e1183d4fed7abb1ec1be1d7efa5f88
url="https://raw.githubusercontent.com/notofonts/notofonts.github.io/$commit/fonts/NotoSerif/hinted/ttf/NotoSerif-Regular.ttf"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir "$tmp/ttf" "$tmp/out"
curl -sSfL -o "$tmp/ttf/NotoSerif-Regular.ttf" "$url"
echo "$sha256  $tmp/ttf/NotoSerif-Regular.ttf" | shasum -a 256 -c --quiet
build_pbf_glyphs "$tmp/ttf" "$tmp/out" >/dev/null
mkdir -p "style/fonts/Noto Serif Regular"
cp "$tmp/out/NotoSerif-Regular/0-255.pbf" "style/fonts/Noto Serif Regular/0-255.pbf"
echo "style/fonts/Noto Serif Regular/0-255.pbf"
