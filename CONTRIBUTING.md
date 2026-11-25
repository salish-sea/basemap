# Contributing

Contributions are welcome. Before starting on one, please [open an issue](https://github.com/salish-sea/basemap/issues/new) that says what you are drawing the map for, and what you want changed and why.

This file says how the basemap is built, pictured and published. What it is and how to use it is in the [README](README.md).

## Prerequisites

**To work on the style and build the test window,** on macOS or Linux:

- **Node,** at the version in [.nvmrc](.nvmrc), with pnpm, which `corepack enable pnpm` provides.
- **uv,** which runs the Python scripts, each with the packages its lockfile pins.
- **GDAL's command-line tools** (`ogr2ogr`, `gdalwarp` and the rest), **tippecanoe**, the **`pmtiles`** command and **`bsdtar`**.
- For the README's pictures: **`cwebp`**, and Playwright's Chromium, installed once with `pnpm exec playwright install chromium`.

On macOS, with Homebrew, `brew install gdal tippecanoe pmtiles webp uv`; `bsdtar` is part of macOS. On Debian or Ubuntu, `apt install gdal-bin libarchive-tools webp`, then install tippecanoe from [its repository](https://github.com/felt/tippecanoe), `pmtiles` from [its releases](https://github.com/protomaps/go-pmtiles/releases) and uv from [its installer](https://docs.astral.sh/uv/getting-started/installation/). The full builds use the versions pinned in [builder/Dockerfile](builder/Dockerfile).

**To build the whole coast and publish it,** as well:

- **Docker,** and about 15 GB of disk for the source grids, 30 GB for the working files, and 16 GB of memory.
- **An NVIDIA graphics card that Docker can use,** for drawing the image tiles (see [Building the whole coast](#building-the-whole-coast)).
- **The publisher's key,** for uploading to tiles.salishsea.io, and the GitHub command line, `gh`, for announcing a version.

Remaking the depth labels' serif glyphs, which are checked in, also needs `cargo install build_pbf_glyphs`.

## Making a change

- **Record a decision before moving on.** Decisions about what the map is built from, how it is drawn and how it is served are in [decisions/](decisions/), each with what was rejected.
- **Say what the change does for someone using the map** under `## Unreleased` in [CHANGELOG.md](CHANGELOG.md), in the same pull request. A change to the build alone needs no entry.
- **Redraw the README's pictures** after a change to how the map looks, and commit them with it (see [Pictures](#pictures)).

## Building

The style is [style/style.ts](style/style.ts), built on Protomaps' light flavour, and the build is the [Makefile](Makefile). Source grids are downloaded once into `cache/`, which is not committed.

```sh
pnpm install
make             # every archive for a test window around Haro Strait, in build/window/; the fonts and icons, in build/assets/; and the labels' fonts, with the depth labels' serif, in build/fonts/
make serve       # the comparison page: our map beside the same map without its relief
make images      # the image tiles, in build/window/images/: about 7 tiles a second in software, and about 100 on a graphics card
make places      # the place lists a site can search, in build/window/places-*.json
```

The comparison page keeps its view and choices in the URL, so a view can be shared: `#zoom/lat/lon` for the view, `?left=ours&right=flat` for the two maps, `?strength=0.25` for the relief, and `?base=/coast/` to draw from `build/coast/` rather than `build/window/`.

Each Python script lists its packages at its top, and `uv run` installs the versions in the lockfile beside it, such as `scripts/names.py.lock`. Those packages bring their own GDAL, GEOS and PROJ, separate from the GDAL of `ogr2ogr` and `gdalwarp`, so a lockfile keeps a script's results from changing under it. Give a new script its lockfile with `uv lock --script scripts/<name>.py`, and move one forward with `uv lock --script --upgrade scripts/<name>.py`.

The whole range, `make REGION=coast`, is too big for a laptop, so it is built in Docker on hostess, Peter's desktop ([decision 021](decisions/021-full-builds-run-on-hostess.md)); see [Building the whole coast](#building-the-whole-coast).

## Pictures

The README's pictures are drawn from a build, not taken by hand, so that they show the map as it is:

```sh
make pictures VERSION=2026.10.3   # from a published version, drawn by its own comparison page
make pictures REGION=coast        # from this machine's build; the window draws the views inside it and keeps the rest
```

[scripts/pictures.ts](scripts/pictures.ts) holds the list of views. It draws each in the comparison page with `?picture`, which shows one map without controls, in headless Chromium, and writes it to `docs/images/` as WebP.

### Labels that come and go

A label can lose its place to another as the map is zoomed in, which no picture at one zoom shows. Before a release that changes labels, sweep them:

```sh
node scripts/label_sweep.ts 2026.10.16 build/coast/salmon.geojsons --landmarks=build/coast/landmarks.pmtiles
node scripts/label_sweep.ts 2026.10.16 build/coast/peninsulas.geojsons --landmarks=build/coast/landmarks.pmtiles --layer=peninsula_labels
```

The sweep builds the comparison page against a published version, with this build's landmarks archive in place of that version's. It centres the map on each label, zooms from the label's first zoom to 15, and lists any label that is drawn and then isn't ([decision 020](decisions/020-each-river-mouth-is-labelled-with-its-salmon-runs.md)). It looks for the salmon runs' labels unless `--layer` names other layers. It looks only within about 150 pixels of each label's point, so it misses a label drawn from a different point, as Protomaps draws its islands' names, once the map is zoomed far enough in: sweep those from Protomaps' own points.

## Publishing

[infra/](infra/) holds the CDK stack for tiles.salishsea.io, in Orcasound's AWS account: a private bucket behind CloudFront in us-west-2, and a `basemap-publisher` user that can add files but never change or delete them.

```sh
(cd infra && pnpm install && pnpm cdk deploy --all --profile orcasound)   # once, and after changing infra/
builder/run.sh coast 2026.10.2  # build the whole range in Docker on hostess, and publish it as 2026.10.2
scripts/publish.sh 2026.10.2    # publish this machine's build of the window
scripts/release.sh 2026.10.2    # once the publish has finished: announce the version
```

### Before building

Move `PROTOMAPS_BUILD` in the [Makefile](Makefile) to the newest daily build at [build.protomaps.com](https://build.protomaps.com/), in its own commit. Protomaps keeps only about a week of builds, so an older pin can't be extracted again ([decision 022](decisions/022-the-protomaps-build-is-moved-forward-before-each-version.md)).

### Building the whole coast

`builder/run.sh` builds the Docker image from this checkout and runs it in the background, with `~/basemap-data` (or `$BASEMAP_DATA`) at `/data`, where the source grids are kept between builds and the build is written.

- **It leaves the machine usable.** Make runs six steps at once ([builder/build.sh](builder/build.sh)). The container may use all but 4 GB of the machine's memory, without swap, so a build that runs short of memory is stopped rather than making the desktop stop answering. It may use all but four of the machine's cores, eight on hostess.
- **It needs an NVIDIA graphics card,** on which Chromium draws the image tiles; in this image, Chromium's software renderer times out on every page, so run.sh refuses to start without one. Tell Docker about the card once: install NVIDIA's container toolkit from [NVIDIA's apt repository](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html#with-apt-ubuntu-debian), then describe the card with `sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml`.
- **Follow it** with `docker logs -f basemap-build`. Each build also keeps its log in `build/<region>/logs/`, named for when it started. Its first line names the commit, the CPUs and make's jobs, and the image step's `drawing with …` line names the renderer that drew the tiles. Beside it, a `.timing.jsonl` file has a line for each of make's steps, with how long it took, its CPU time and memory, and its command ([builder/timed-shell.py](builder/timed-shell.py)), so a build's times can be compared with earlier ones.
- **Publishing reads the publisher's key** from `~/.config/basemap/publisher.env`, as `AWS_ACCESS_KEY_ID=` and `AWS_SECRET_ACCESS_KEY=` lines. Only its owner may read it (`chmod 600`); run.sh refuses it otherwise. It was created with `aws iam create-access-key --user-name basemap-publisher`.

### What a publish does

See [decision 007](decisions/007-published-builds-are-dated-and-never-change.md).

- **It numbers the version in CalVer,** as the [animals register](https://github.com/salish-sea/animals#versioning) numbers its releases: the year, the month, and a count within the month.
- **It tags the commit** with the version, and pushes the tag first ([scripts/release-tag.sh](scripts/release-tag.sh)). The checkout must be clean and on origin's `main`. A tag never moves: if a build fails and the fix is a new commit, that number is skipped.
- **It stores each archive once,** as `archives/<archive>-<hash>.pmtiles`, named for its contents, and uploads only the ones not already there. A version that changes only the style uploads about 2 MB.
- **It stores the image tiles once,** as `images/<hash>/`, named for their contents, and names them in the style ([decision 014](decisions/014-image-tiles-are-drawn-from-the-style-along-the-shore.md)). Their list, `tiles.txt`, goes up last, as the sign that they are all there.
- **It uploads the fonts and icons** the style names, under a path for their commit, if they aren't there yet ([decision 010](decisions/010-fonts-and-icons-are-served-with-the-tiles.md)), and the labels' fonts, with the depth labels' serif, as `assets/fonts-<hash>/`, named for their contents ([decision 017](decisions/017-depth-labels-are-set-in-a-serif.md)). `scripts/serif_glyphs.sh` remakes the serif's glyphs.
- **It stores the place lists once,** as `places/<list>-<hash>.json`, named for their contents, and names them in the style ([decision 018](decisions/018-the-names-the-map-labels-are-published-as-lists.md)).
- **It writes an index page,** `<version>/index.html` ([scripts/version_index.ts](scripts/version_index.ts)), with `names.tsv` beside it ([scripts/version_names.ts](scripts/version_names.ts)). The page shows the version's map and every name it labels, and links every file the version is made of. Without it, the style would be the only record of which image tiles, place lists and archives belong to a version, since those are named for their contents.
- **It uploads `style.json` last,** as the sign that the version is complete, and refuses a version that already has one. To finish a publish that failed partway, run it again from the same commit.

### Announcing a version

When the publish has finished, run `scripts/release.sh 2026.10.2` from a checkout, then commit the README and changelog it updates.

- **It makes the version's GitHub release** on its tag. The notes are what the changelog said under Unreleased at the tag, so changes merged since the tag aren't included, followed by links to the version's index page and files.
- **It moves those entries** in the checkout's CHANGELOG.md into a section for the version, dated the day it is announced ([scripts/changelog-section.ts](scripts/changelog-section.ts)). It refuses to run if the changelog said nothing about the version.
- **It points the README** at the version's index page and style ([scripts/readme-version.ts](scripts/readme-version.ts)).

It runs after the publish rather than with the tag, because a failed build skips its number, and a release made with the tag could announce a version that was never published.
