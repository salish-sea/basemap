# Contributing

Contributions are welcome. Before starting on one, please [open an issue](https://github.com/salish-sea/basemap/issues/new) that describes your context, such as what you are drawing the map for, and what you want changed and why.

How the basemap is built, pictured and published. What it is and how to use it is in the [README](README.md). Decisions about what it is built from, how it is drawn and how it is served are recorded in [decisions/](decisions/), each with what was rejected; when a decision is made, the record is written before moving on.

## Building

The style is [style/style.ts](style/style.ts), built on Protomaps' light flavour; the build is the [Makefile](Makefile). It needs GDAL, tippecanoe, the `pmtiles` command, `bsdtar` (part of macOS; `libarchive-tools` on Debian), `uv` and Node (version in [.nvmrc](.nvmrc)). Source grids are downloaded once into `cache/`, which is not committed.

```sh
pnpm install
make             # every archive for a test window around Haro Strait, in build/window/, the fonts and icons, in build/assets/, and the labels' fonts with the depth labels' serif, in build/fonts/
make serve       # a page that compares our map with Esri's, side by side
make images      # the image tiles, in build/window/images/; slow, about 7 tiles a second
make places      # the place names as lists a site can search, in build/window/places-*.json
```

The whole range, `make REGION=coast`, needs about 12 GB of source grids and 30 GB of working files, so it is built on a Fly machine with 8 CPUs and 16 GB of memory ([decision 008](decisions/008-full-builds-run-on-a-fly-machine.md)); see Publishing.

The comparison page keeps its view and choices in the URL, so a view can be shared: `#zoom/lat/lon` for the view, `?left=ours&right=esri` for the two maps, `?strength=0.25` for the relief, and `?base=/coast/` to draw from `build/coast/` rather than `build/window/`.

## Pictures

The README's pictures are drawn from a build rather than taken by hand, so that they show the map as it is:

```sh
make pictures VERSION=2026.10.3   # from a published version, drawn by its own comparison page
make pictures REGION=coast        # from this machine's build; the window draws the views inside it and keeps the rest
```

[scripts/pictures.ts](scripts/pictures.ts) holds the list of views. It draws each in the comparison page with `?picture`, which shows one map without controls, in headless Chromium, and writes it to `docs/images/` as WebP. It needs `cwebp`, and Playwright's Chromium, installed once with `pnpm exec playwright install chromium`. Redraw the pictures after a change to how the map looks, and commit them with it.

## Publishing

[infra/](infra/) holds the CDK stack for tiles.salishsea.io, in Orcasound's AWS account: a private bucket behind CloudFront in us-west-2, and a `basemap-publisher` user that can add files but never change or delete them.

```sh
(cd infra && pnpm install && pnpm cdk deploy --all --profile orcasound)   # once, and after changing infra/
fly/run.sh coast 2026.10.2      # build the whole range on a Fly machine and publish it
scripts/publish.sh 2026.10.2    # publish this machine's build of the window
```

What a publish does ([decision 007](decisions/007-published-builds-are-dated-and-never-change.md)):

- **It numbers the version in CalVer**, as the [animals register](https://github.com/salish-sea/animals#versioning) numbers its releases: the year, the month, and a count within the month.
- **It tags the commit** with the version and pushes the tag first ([scripts/release-tag.sh](scripts/release-tag.sh)). The checkout must be clean and on origin's `main`. A tag never moves: if a build fails and the fix is a new commit, that number is skipped.
- **It stores each archive once,** as `archives/<archive>-<hash>.pmtiles`, named for its contents, and uploads only the ones not already there. A version that changes only the style uploads about 2 MB.
- **It stores the image tiles once,** as `images/<hash>/`, named for their contents, and names them in the style ([decision 014](decisions/014-image-tiles-are-drawn-from-the-style-along-the-shore.md)). Their list, `tiles.txt`, goes up last, as the sign that they are all there.
- **It uploads the fonts and icons** the style names, under a path for their commit, if they aren't there yet ([decision 010](decisions/010-fonts-and-icons-are-served-with-the-tiles.md)), and the labels' fonts with the depth labels' serif under `assets/fonts-<hash>/`, named for their contents ([decision 017](decisions/017-depth-labels-are-set-in-a-serif.md)). The serif's glyphs are checked in; `scripts/serif_glyphs.sh` remakes them, and needs `cargo install build_pbf_glyphs`.
- **It stores the place-name lists once,** as `places/<list>-<hash>.json`, named for their contents, and names them in the style ([decision 018](decisions/018-the-names-the-map-labels-are-published-as-lists.md)).
- **It writes an index page,** `<version>/index.html`, that links every file the version is made of ([scripts/version_index.ts](scripts/version_index.ts)). The style is otherwise the only record of which image tiles, place lists and archives belong to a version, since those are named for their contents.
- **It uploads `style.json` last,** as the sign that the version is complete, and refuses a version that already has one. A publish that failed partway is finished by running it again from the same commit.

When the publish has finished, announce the version from a checkout with `scripts/release.sh 2026.10.2`, then commit the README it updates. It makes the version's GitHub release on its tag, linking the version's index page, and lists the version's files in the README ([scripts/readme-version.ts](scripts/readme-version.ts)). It runs after the publish rather than with the tag because a failed build skips its number, and a release made with the tag could announce a version that was never published.

`fly/run.sh` builds the image from this checkout and runs it on an 8-CPU machine with the app's volume, which keeps the source grids between builds; the machine is removed when the build ends. Follow it with `fly logs -a salishsea-basemap-build`. The publisher's key is a secret of the Fly app, created with `aws iam create-access-key --user-name basemap-publisher` and set by hand.
