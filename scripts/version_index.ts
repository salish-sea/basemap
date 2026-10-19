// Writes a version's index page, which links every file the version is made of, so that
// someone can find them without reading the style (decisions/007):
//   node scripts/version_index.ts 2026.10.14 build/publish/2026.10.14/style.json build/coast > index.html
// The image tiles, the place lists and the archives are named for their contents, not the
// version (decisions/014, 018), so the style is the only record of which belong to it; this
// page reads them from there. What each place list holds, its licence and its count of
// places, it reads from the lists in the region's build, the same files publish.sh uploads.

import { readFileSync } from 'node:fs';

const [version, stylePath, src] = process.argv.slice(2);
if (!version || !stylePath || !src) {
  console.error('usage: node scripts/version_index.ts VERSION STYLE.json BUILD_DIR');
  process.exit(2);
}
const style = JSON.parse(readFileSync(stylePath, 'utf8'));
const base = `https://tiles.salishsea.io/${version}`;
const repo = 'https://github.com/salish-sea/basemap';

const escape = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!);
const link = (url: string) => `<a href="${escape(url)}">${escape(url)}</a>`;
const row = (name: string, what: string) => `<tr><th scope="row">${name}</th><td>${what}</td></tr>`;

const images: string | undefined = style.metadata?.['salishsea:images'];
const places: Record<string, string> = style.metadata?.['salishsea:places'] ?? {};
const lists = Object.entries(places).map(([name, url]) => {
  const list = JSON.parse(readFileSync(`${src}/places-${name}.json`, 'utf8'));
  return `<li><p>${link(url)}</p><p>${escape(list.about)}. ${list.places.length.toLocaleString('en')} places. ` +
    `${escape(list.licence)}; credit “${escape(list.attribution)}”.</p></li>`;
});
const archives = Object.entries(style.sources as Record<string, { url?: string }>)
  .filter(([, source]) => source.url?.startsWith('pmtiles://'))
  .map(([name, source]) => row(`<code>${escape(name)}</code>`, link(source.url!.slice('pmtiles://'.length))));

process.stdout.write(`<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Basemap ${escape(version)}</title>
<style>
  :root { color-scheme: light dark; --ink: #1d2a33; --muted: #5b6b75; --rule: #d5dde2; --page: #fbfcfd; --link: #1f5f8b; }
  @media (prefers-color-scheme: dark) { :root { --ink: #e3eaee; --muted: #9aabb5; --rule: #34434d; --page: #131b20; --link: #8cc4ec; } }
  body { margin: 0 auto; max-width: 52rem; padding: 2rem 16px 4rem; background: var(--page); color: var(--ink);
    font: 16px/1.5 system-ui, sans-serif; }
  h1 { font-size: 1.6rem; margin: 0 0 .25rem; } h2 { font-size: 1.15rem; margin: 2rem 0 .5rem; }
  p { margin: .4rem 0; } .muted { color: var(--muted); } a { color: var(--link); overflow-wrap: anywhere; }
  code { font-size: .92em; overflow-wrap: anywhere; } ul { padding-left: 1.2rem; } li { margin-bottom: .75rem; }
  table { border-collapse: collapse; width: 100%; } th, td { text-align: left; vertical-align: top; padding: .35rem .5rem .35rem 0;
    border-top: 1px solid var(--rule); } th { font-weight: 600; white-space: nowrap; }
</style>
</head>
<body>
<h1>Salish Sea basemap ${escape(version)}</h1>
<p class="muted">The files of this version of the basemap, built from the commit tagged <a href="${repo}/tree/${escape(version)}">${escape(version)}</a>. None of them ever changes, so a page can name them and cache them for a year. How to use them is in the <a href="${repo}#readme">README</a>.</p>

<h2>The map</h2>
<table><tbody>
${row('Style', link(`${base}/style.json`))}
${row('Comparison page', link(`${base}/viewer/index.html`))}
</tbody></table>
${images ? `
<h2>Image tiles</h2>
<p>For stitching into a picture rather than drawing a map: 256-pixel tiles, each drawn at 512 pixels, without labels. Put a tile's zoom and position in place of <code>{z}</code>, <code>{x}</code> and <code>{y}</code>.</p>
<p><code>${escape(images)}</code></p>
<p>They cover only some of the map at the closer zooms, so the tiles there are listed, one <code>z x y</code> to a line: ${link(images.replace('{z}/{x}/{y}.webp', 'tiles.txt'))}</p>
` : ''}${lists.length ? `
<h2>Place names</h2>
<p>For a search that takes people to a place on the map. Each list gives its places as rows of its <code>columns</code>: the name, its kind, a longitude and latitude to look at, a zoom to look from (MapLibre's), and any other names it goes by.</p>
<ul>
${lists.join('\n')}
</ul>
` : ''}
<h2>Vector and elevation tiles</h2>
<p>The <a href="https://docs.protomaps.com/pmtiles/">PMTiles</a> archives the style draws from, by the name of the style's source.</p>
<table><tbody>
${archives.join('\n')}
</tbody></table>
</body>
</html>
`);
