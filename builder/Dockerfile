# syntax=docker/dockerfile:1
#
# The basemap's build machine (decisions 008 and 021): everything `make REGION=coast` and
# scripts/publish.sh need, with this repository at the commit the image is built from.
# builder/run.sh builds it and runs it with a directory of the host at /data, which keeps
# the source grids between builds and holds the working files.
#
# Every base image is pinned by its digest, with its tag beside it for people: a tag can be
# moved to a new image, and the GDAL image's tools are what the archives are made with.
# To move one forward, look up the new tag's digest with
#   docker buildx imagetools inspect <image>:<tag>
# Node's matches .nvmrc. The Python scripts' packages, which bring their own GDAL, GEOS and
# PROJ, are pinned by the lockfile beside each script (scripts/*.py.lock).

# --- tippecanoe, built from source: Ubuntu's package is years behind ----------------
FROM ubuntu:24.04@sha256:68ee22004a9109b44973313b02ff7b1de250f1de0f5ecb628d73f579aaff33ac AS tippecanoe
ARG TIPPECANOE_VERSION=2.79.0
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential ca-certificates curl libsqlite3-dev zlib1g-dev \
 && rm -rf /var/lib/apt/lists/*
RUN curl -sSfL https://github.com/felt/tippecanoe/archive/refs/tags/${TIPPECANOE_VERSION}.tar.gz | tar -xz \
 && make -C tippecanoe-${TIPPECANOE_VERSION} -j"$(nproc)" \
 && make -C tippecanoe-${TIPPECANOE_VERSION} install PREFIX=/opt/tippecanoe

FROM node:24.22.1-bookworm-slim@sha256:55fb5f5a527ea2c5c4a95f963e48ef90aa38c7b346054fdc8ee9957a2b55d205 AS node
FROM ghcr.io/astral-sh/uv:0.13.0@sha256:cdc6093146eb3ff6a40107b38f008b789e050e77ad87865e381d9917da55a168 AS uv

# --- the build machine ---------------------------------------------------------
# The full image, because NOAA's grids are NetCDF, which the small one can't read.
FROM ghcr.io/osgeo/gdal:ubuntu-full-3.13.3@sha256:2dd0f81ef927ff4c3d4dbe4f73c029dc86d4073974c0564f8e196f6e1412e2e0
ARG PMTILES_VERSION=1.31.2
ARG AWSCLI_VERSION=2.37.12
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl git libarchive-tools libsqlite3-0 make unzip zlib1g \
 && rm -rf /var/lib/apt/lists/*
COPY --from=tippecanoe /opt/tippecanoe/bin/ /usr/local/bin/
COPY --from=node /usr/local/bin/node /usr/local/bin/
COPY --from=node /usr/local/lib/node_modules/corepack /usr/local/lib/node_modules/corepack
COPY --from=uv /uv /uvx /usr/local/bin/
RUN ln -s ../lib/node_modules/corepack/dist/corepack.js /usr/local/bin/corepack && corepack enable pnpm
RUN curl -sSfL https://github.com/protomaps/go-pmtiles/releases/download/v${PMTILES_VERSION}/go-pmtiles_${PMTILES_VERSION}_Linux_x86_64.tar.gz \
  | tar -xz -C /usr/local/bin pmtiles
RUN curl -sSfL -o /tmp/awscli.zip https://awscli.amazonaws.com/awscli-exe-linux-x86_64-${AWSCLI_VERSION}.zip \
 && unzip -q /tmp/awscli.zip -d /tmp && /tmp/aws/install && rm -rf /tmp/aws /tmp/awscli.zip

WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN COREPACK_ENABLE_DOWNLOAD_PROMPT=0 pnpm install --frozen-lockfile
# Chromium, and the libraries it needs, for drawing the image tiles (decisions/014).
RUN pnpm exec playwright install --with-deps chromium && rm -rf /var/lib/apt/lists/*
COPY . .
# uv's downloaded Python and packages live in /data, so later builds reuse them.
ENV UV_CACHE_DIR=/data/uv-cache UV_PYTHON_INSTALL_DIR=/data/uv-python
ENTRYPOINT ["builder/build.sh"]
