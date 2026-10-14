# 007 — Published builds are dated and never change

**Status:** accepted · **Decided:** 2026-10-13 · **Follows:** SalishSea.io's [074](https://github.com/salish-sea/salishsea-io/blob/main/docs/decisions/074-the-basemap-is-its-own-project-and-the-cards-draw-on-it.md), which put the basemap at tiles.salishsea.io with a versioned path per build

## Decision

**Each build is published under a path named for its date,** such as `https://tiles.salishsea.io/2026-10-13/`, with a letter for a second build that day (`2026-10-13b`). [scripts/publish.sh](../scripts/publish.sh) refuses a version that already exists, so a page that names a version always gets the same map. That is why every file can be cached for a year, by browsers and by CloudFront, and why nothing needs to be invalidated after a publish.

**Each version holds** the archives, `style.json` pointing at them, and the comparison page at `viewer/index.html`, for trying a build out before a site switches to it.

**Any site may fetch the map.** Every response allows any origin, so SalishSea.io, Orcasound or anyone else can draw it.

**The stack is in us-east-1,** in Orcasound's AWS account ([infra/](../infra/)). CloudFront only accepts certificates from that region, so keeping everything there lets the stack make and validate its own certificate through the salishsea.io zone, with nothing made by hand. Unlike SalishSea.io, the basemap is deployed and published from a maintainer's machine, not by GitHub Actions: a build needs about 9 GB of cached source grids.

## Rejected

- **A moving "latest" path.** A page using it would change under its users at each publish, and its files couldn't be cached for long. A site picks a version and moves to a newer one deliberately.
- **Version numbers.** A date says how old the data is, which is what a reader of the map needs to know.
