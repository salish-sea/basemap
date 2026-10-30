# Contributing

Contributions are welcome. Before starting on one, please [open an issue](https://github.com/salish-sea/basemap/issues/new) that describes your context, such as what you are drawing the map for, and what you want changed and why.

How the basemap is built, pictured and published. What it is and how to use it is in the [README](README.md). Decisions about what it is built from, how it is drawn and how it is served are recorded in [decisions/](decisions/), each with what was rejected; when a decision is made, the record is written before moving on.

## Building

The style is [style/style.ts](style/style.ts), built on Protomaps' light flavour; the build is the [Makefile](Makefile). It needs GDAL, tippecanoe, the `pmtiles` command, `bsdtar` (part of macOS; `libarchive-tools` on Debian), `uv` and Node (version in [.nvmrc](.nvmrc)). Source grids are downloaded once into `cache/`, which is not committed.

Each Python script declares its packages at its top and runs with `uv run`, which installs the versions in the lockfile beside it, such as `scripts/names.py.lock`. Those packages bring their own GDAL, GEOS and PROJ, apart from the GDAL that `ogr2ogr` and `gdalwarp` are, so a lockfile keeps a script's results from changing under it. Give a new script its lockfile with `uv lock --script scripts/<name>.py`, and move one forward with `uv lock --script --upgrade scripts/<name>.py`. The full builds' image pins its tools and base images by digest ([builder/Dockerfile](builder/Dockerfile)).

```sh
pnpm install
make             # every archive for a test window around Haro Strait, in build/window/, the fonts and icons, in build/assets/, and the labels' fonts with the depth labels' serif, in build/fonts/
make serve       # a page that shows our map with and without its relief, side by side
make images      # the image tiles, in build/window/images/; slow, about 7 tiles a second
make places      # the place names as lists a site can search, in build/window/places-*.json
```

The whole range, `make REGION=coast`, needs about 15 GB of source grids, 30 GB of working files and more than 16 GB of memory, so it is built in Docker on hostess, Peter's desktop ([decision 021](decisions/021-full-builds-run-on-hostess.md)); see Publishing.

The comparison page keeps its view and choices in the URL, so a view can be shared: `#zoom/lat/lon` for the view, `?left=ours&right=flat` for the two maps, `?strength=0.25` for the relief, and `?base=/coast/` to draw from `build/coast/` rather than `build/window/`.

## Pictures

The README's pictures are drawn from a build rather than taken by hand, so that they show the map as it is:

```sh
make pictures VERSION=2026.10.3   # from a published version, drawn by its own comparison page
make pictures REGION=coast        # from this machine's build; the window draws the views inside it and keeps the rest
```

[scripts/pictures.ts](scripts/pictures.ts) holds the list of views. It draws each in the comparison page with `?picture`, which shows one map without controls, in headless Chromium, and writes it to `docs/images/` as WebP. It needs `cwebp`, and Playwright's Chromium, installed once with `pnpm exec playwright install chromium`. Redraw the pictures after a change to how the map looks, and commit them with it.

### Labels that come and go

A label can lose its place to another as the map is zoomed in, which no picture at one zoom shows. Before a release that changes labels, sweep them:

```sh
node scripts/label_sweep.ts 2026.10.16 build/coast/salmon.geojsons --landmarks=build/coast/landmarks.pmtiles
node scripts/label_sweep.ts 2026.10.16 build/coast/peninsulas.geojsons --landmarks=build/coast/landmarks.pmtiles --layer=peninsula_labels
```

It builds the comparison page against a published version, puts this build's landmarks' archive in place of that version's, centres the map on each label and zooms it from the label's first zoom to 15, and lists any label that is drawn and then isn't ([decision 020](decisions/020-each-river-mouth-is-labelled-with-its-salmon-runs.md)). It looks for the salmon runs' labels unless `--layer` names other layers, and only within about 150 pixels of each label's point, so a label drawn from another point, as Protomaps draws its islands' names, is missed once the map is zoomed far enough in: sweep those from Protomaps' own points.

## Publishing

[infra/](infra/) holds the CDK stack for tiles.salishsea.io, in Orcasound's AWS account: a private bucket behind CloudFront in us-west-2, and a `basemap-publisher` user that can add files but never change or delete them.

```sh
(cd infra && pnpm install && pnpm cdk deploy --all --profile orcasound)   # once, and after changing infra/
builder/run.sh coast 2026.10.2  # build the whole range in Docker on hostess and publish it
scripts/publish.sh 2026.10.2    # publish this machine's build of the window
```

Before building a version to publish, move `PROTOMAPS_BUILD` in the [Makefile](Makefile) to the newest daily build at [build.protomaps.com](https://build.protomaps.com/), in its own commit: Protomaps keeps only about a week of them, so an older pin can't be extracted again ([decision 022](decisions/022-the-protomaps-build-is-moved-forward-before-each-version.md)).

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

`builder/run.sh` builds the image from this checkout and runs it in the background with `~/basemap-data` (or `$BASEMAP_DATA`) at `/data`, which keeps the source grids between builds and holds the build. Follow it with `docker logs -f basemap-build`; the container is kept until the next build starts, so its log can still be read. The publisher's key is in `~/.config/basemap/publisher.env`, as `AWS_ACCESS_KEY_ID=` and `AWS_SECRET_ACCESS_KEY=` lines, readable only by its owner (`chmod 600`; run.sh refuses it otherwise); it was created with `aws iam create-access-key --user-name basemap-publisher`.
