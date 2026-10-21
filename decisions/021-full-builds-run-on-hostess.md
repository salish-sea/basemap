# 021 — Full builds run in Docker on hostess

**Status:** accepted · **Decided:** 2026-10-20, by Peter · **Supersedes:** [008](008-full-builds-run-on-a-fly-machine.md)

## Context

[008](008-full-builds-run-on-a-fly-machine.md) moved full builds to a temporary Fly machine because no machine of Peter's had room for them. The whole range, Monterey Bay to Haida Gwaii, needs about 15 GB of source grids and 30 GB of working files, and its elevation tiles need more than 16 GB of memory at their peak. The Fly machine kept its source grids on a 100 GB volume, which cost about $15 a month whether or not anything was built.

hostess, Peter's desktop, now has room: a Ryzen 5 5600 with 6 cores and 12 threads, 32 GB of memory, and over 300 GB free. It runs Linux in WSL2, which is given 28 GB of that memory, and Docker inside it.

## Decision

**Full builds run in Docker on hostess.** [builder/run.sh](../builder/run.sh) builds the same image as before from [builder/Dockerfile](../builder/Dockerfile) at the current checkout and runs [builder/build.sh](../builder/build.sh) in it, with `~/basemap-data` (or `$BASEMAP_DATA`) at `/data`. That directory keeps the source grids between builds, as the volume did, and holds the working files and archives. Given a version, the build publishes it.

**It publishes as `basemap-publisher`,** with the key that was the Fly app's secret, now in `~/.config/basemap/publisher.env` on hostess, readable only by Peter. run.sh passes it to the container only when it publishes.

The image still pins its tools, so a build doesn't depend on what hostess happens to have installed, and the test window still builds anywhere with `make`.

## Consequences

- The Fly app `salishsea-basemap-build` and its volume are deleted once hostess has published a version. The source grids were copied off the volume first and checked against their checksums, so GEBCO's grid, which took CEDA five hours to deliver, needn't be downloaded again.
- Builds depend on one machine. If hostess is unavailable, the Fly route in 008 can be rebuilt from git history; it needs only a new app and volume, and the first build downloads the grids again.

## Rejected

- **Keeping the Fly machine.** It worked, but its volume cost money every month to save a download, and hostess's 12 threads at desktop clocks and 28 GB of memory are at least a match for its 8 server CPUs and 16 GB.
- **Installing the tools on hostess directly.** GDAL with NetCDF, tippecanoe built from source, pmtiles, Node, uv, the AWS CLI and Chromium would then drift with Ubuntu's updates; the image pins them, and it is the image the Fly builds already used.
