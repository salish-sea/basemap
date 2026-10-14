# Contributing

How the basemap is built, pictured and published. What it is and how to use it is in the [README](README.md). Decisions about what it is built from, how it is drawn and how it is served are recorded in [decisions/](decisions/), each with what was rejected; when a decision is made, the record is written before moving on.

## Building

The style is [style/style.ts](style/style.ts), built on Protomaps' light flavour; the build is the [Makefile](Makefile). It needs GDAL, tippecanoe, the `pmtiles` command, `bsdtar` (part of macOS; `libarchive-tools` on Debian), `uv` and Node (version in [.nvmrc](.nvmrc)). Source grids are downloaded once into `cache/`, which is not committed.

```sh
pnpm install
make             # every archive for a test window around Haro Strait, in build/window/
make serve       # a page that compares our map with Esri's, side by side
```

The whole range, `make REGION=coast`, needs about 12 GB of source grids and 30 GB of working files, so it is built on a Fly machine with 8 CPUs and 16 GB of memory ([decision 008](decisions/008-full-builds-run-on-a-fly-machine.md)); see Publishing.

The comparison page keeps its view and choices in the URL, so a view can be shared: `#zoom/lat/lon` for the view, `?left=ours&right=esri` for the two maps, `?strength=0.25` for the relief, and `?base=/coast/` to draw from `build/coast/` rather than `build/window/`.

## Pictures

The README's pictures are drawn from a build rather than taken by hand, so that they show the map as it is:

```sh
make pictures REGION=coast   # or the window, which draws the views inside it and keeps the rest
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
- **It uploads `style.json` last,** as the sign that the version is complete, and refuses a version that already has one. A publish that failed partway is finished by running it again from the same commit.

`fly/run.sh` builds the image from this checkout and runs it on an 8-CPU machine with the app's volume, which keeps the source grids between builds; the machine is removed when the build ends. Follow it with `fly logs -a salishsea-basemap-build`. The publisher's key is a secret of the Fly app, created with `aws iam create-access-key --user-name basemap-publisher` and set by hand.
