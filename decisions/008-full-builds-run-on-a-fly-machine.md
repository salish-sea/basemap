# 008 — Full builds run on a Fly machine

**Status:** superseded by [021](021-full-builds-run-on-hostess.md) on 2026-10-20 · **Decided:** 2026-10-13, by Peter · **Follows:** [007](007-published-builds-are-dated-and-never-change.md)

## Context

The whole range, Monterey Bay to Haida Gwaii, is about 105 times the area of the Haro Strait test window. Its build needs about 12 GB of source grids and roughly 30 GB of working files, more than a maintainer's laptop or maderas, Peter's small server, has free, and several hours on two CPUs.

## Decision

**Full builds run on a temporary Fly machine** in Orcasound's Fly organization: the app `salishsea-basemap-build`, with a 100 GB volume in `sjc` that keeps the source grids between builds. [fly/run.sh](../fly/run.sh) builds the image from [fly/Dockerfile](../fly/Dockerfile) at the current checkout, runs [fly/build.sh](../fly/build.sh) on an 8-CPU machine, and removes the machine when the build ends. Given a version, the build publishes it.

**The image pins its tools:** GDAL, tippecanoe built from source, the `pmtiles` tool, Node, uv and the AWS CLI, so a build doesn't depend on what a maintainer happens to have installed.

**It publishes as `basemap-publisher`,** the user from [007](007-published-builds-are-dated-and-never-change.md) that can add files to the bucket but not change or delete them. Its key is a secret of the Fly app, set by hand.

The test window still builds on a laptop with `make`.

## Rejected

- **maderas.** It has 2 CPUs, 3 GB of memory and about 27 GB free; a full build wouldn't fit without freeing space there, and would take hours.
- **Building the coast in pieces and merging the archives.** It would fit a small machine, but needs merging code for every kind of archive, and care at the joins.
