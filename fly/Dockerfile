# syntax=docker/dockerfile:1
#
# The basemap's build machine (decision 008): everything `make REGION=coast` and
# scripts/publish.sh need, with this repository at the commit the image is built from.
# fly/run.sh builds it and runs it on a Fly machine with a volume at /data, which keeps
# the source grids between builds and holds the working files.

ARG NODE_VERSION=24.13

# --- tippecanoe, built from source: Ubuntu's package is years behind ----------------
FROM ubuntu:24.04 AS tippecanoe
ARG TIPPECANOE_VERSION=2.79.0
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential ca-certificates curl libsqlite3-dev zlib1g-dev \
 && rm -rf /var/lib/apt/lists/*
RUN curl -sSfL https://github.com/felt/tippecanoe/archive/refs/tags/${TIPPECANOE_VERSION}.tar.gz | tar -xz \
 && make -C tippecanoe-${TIPPECANOE_VERSION} -j"$(nproc)" \
 && make -C tippecanoe-${TIPPECANOE_VERSION} install PREFIX=/opt/tippecanoe

FROM node:${NODE_VERSION}-bookworm-slim AS node
FROM ghcr.io/astral-sh/uv:0.13.0 AS uv

# --- the build machine ---------------------------------------------------------
# The full image, because NOAA's grids are NetCDF, which the small one can't read.
FROM ghcr.io/osgeo/gdal:ubuntu-full-3.13.3
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
# uv's downloaded Python and packages live on the volume, so later builds reuse them.
ENV UV_CACHE_DIR=/data/uv-cache UV_PYTHON_INSTALL_DIR=/data/uv-python
ENTRYPOINT ["fly/build.sh"]
