# 025 — A Planetiler profile may replace our OpenStreetMap overrides

**Status:** proposed, not decided · **Raised:** 2026-10-22, by Peter, who asked whether there is established tooling for build pipelines like ours

## Context

The basemap is Protomaps' tiles, cut from its daily planet build ([decision 022](022-the-protomaps-build-is-moved-forward-before-each-version.md)), with our own layers drawn over them. Several of those layers exist only to correct a choice Protomaps' build makes, and each corrects it by reading OpenStreetMap again, in Python, and writing a layer of its own with tippecanoe:

- islets that Protomaps keeps only when they are also tagged as coastline ([scripts/islets.py](../scripts/islets.py), decision 018);
- peninsulas, which Protomaps keeps only as points of interest from zoom 12 ([scripts/peninsulas.py](../scripts/peninsulas.py), decision 023);
- landmarks, of which Protomaps' tiles carry almost none, and only from zoom 16 ([scripts/landmarks.py](../scripts/landmarks.py), decision 015);
- next, parks' labels, which Protomaps places at an arbitrary point inside each park, and nature reserves' outlines trimmed to the land.

The style then hides Protomaps' version where ours replaces it. Each such layer is a script, a Makefile rule, a second read of the extracts and a second idea of what a feature is, and both versions have to be kept from showing at once.

Protomaps' tiles are built with [Planetiler](https://github.com/onthegomap/planetiler), and [its basemap](https://github.com/protomaps/basemaps/tree/main/tiles) is one Planetiler profile: Java that decides, for each OpenStreetMap feature, which layer it goes in, where its label sits and from which zoom it appears. The rules our scripts override live there, such as `Earth.java`, which labels every island OpenStreetMap outlines, and `Pois.java`, which places a park's name at any point inside it.

## The option

**Build the Protomaps tiles ourselves, from a fork of its profile with our rules in it,** in place of cutting them from its planet build and drawing corrections over them. The islets, peninsulas and park labels would be changes to the profile's rules, made in one pass over the extracts, and the layers that only correct Protomaps would go.

Other established tools do the same job differently: [OpenMapTiles](https://github.com/openmaptiles/openmaptiles)' toolchain loads OpenStreetMap into PostGIS with imposm3 and defines each layer in YAML and SQL, and [Tilemaker](https://github.com/systemed/tilemaker) defines layers in Lua. Either would mean leaving Protomaps' schema, which our style is built on.

For running the steps, Make is the usual choice for builds from file to file. [Snakemake](https://snakemake.readthedocs.io) and [DVC](https://dvc.org) rerun a step only when its inputs' contents change, rather than their times, which would stop an edit to a comment in the Makefile from marking the ferry routes stale; neither is needed yet.

## What it would cost

- We would follow Protomaps' changes to its profile by merging them, in place of moving the planet build forward (decision 022).
- A build would process the coast's OpenStreetMap extracts with Planetiler, in Java, which takes longer than cutting the planet build; it would run on hostess ([decision 021](021-full-builds-run-on-hostess.md)).
- The overrides are now small Python scripts that anyone can read beside the decision that wanted them; in a fork they would be changes spread through someone else's Java.

## When to decide

Keep the scripts while the overrides are few. Revisit when another override is wanted, or when two of them have to agree about one feature, as the parks' labels and their outlines will.
