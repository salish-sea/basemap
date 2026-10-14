# 007 — Published builds are numbered and never change

**Status:** accepted · **Decided:** 2026-10-13 · **Amended:** 2026-10-14, CalVer, by Peter · **Follows:** SalishSea.io's [074](https://github.com/salish-sea/salishsea-io/blob/main/docs/decisions/074-the-basemap-is-its-own-project-and-the-cards-draw-on-it.md), which put the basemap at tiles.salishsea.io with a versioned path per build

## Decision

**Each build is published under a path named for its version,** such as `https://tiles.salishsea.io/2026.10.1/`. Versions are CalVer, numbered as the [animals register](https://github.com/salish-sea/animals#versioning)'s releases are: the year, the month, and a count within the month, so `2026.10.1`, `2026.10.2`, then `2026.11.1`. The commit a version was built from carries the version as a git tag, pushed before the build or upload starts ([scripts/release-tag.sh](../scripts/release-tag.sh)). A tag never moves. If a build fails and the fix is a new commit, that number is skipped and the fix is published as the next, so no version can mix files built by two commits. (Amended 2026-10-14: versions were first named for their date, with a letter for a second build that day. Peter preferred one versioning scheme across the projects to a new one. The two versions published that way, `2026-10-13` and `2026-10-14`, stay where they are, since published files are never deleted, but nothing uses them.) [scripts/publish.sh](../scripts/publish.sh) uploads `style.json` last, as the sign that a version is complete, and refuses a version that has one, so a page that names a version always gets the same map. A publish that fails partway can be finished by running it again. The `basemap-publisher` user that build machines publish as can only add files, not change or delete them, and the bucket keeps earlier versions of every file, so a mistake can be undone. That is why every file can be cached for a year, by browsers and by CloudFront, and why nothing needs to be invalidated after a publish.

**Each version holds** the archives, `style.json` pointing at them, and the comparison page at `viewer/index.html`, for trying a build out before a site switches to it.

**Any site may fetch the map.** Every response allows any origin, and CORS preflights are answered by the bucket, so SalishSea.io, Orcasound or anyone else can draw it.

**The bucket and distribution are in us-west-2,** in Orcasound's AWS account beside SalishSea.io's own stack ([infra/](../infra/)). CloudFront only accepts certificates from us-east-1, so the certificate has a small stack of its own there, validated through the salishsea.io zone and passed across by CDK, with nothing made by hand. Unlike SalishSea.io, the basemap is deployed and published from a maintainer's machine, not by GitHub Actions: a build needs about 9 GB of cached source grids.

## Rejected

- **A moving "latest" path.** A page using it would change under its users at each publish, and its files couldn't be cached for long. A site picks a version and moves to a newer one deliberately.
- **Version numbers.** A date says how old the data is, which is what a reader of the map needs to know.
