// Writes a version's index page, which links every file the version is made of, so that
// someone can find them without reading the style (decisions/007):
//   node scripts/version_index.ts 2026.10.14 build/publish/2026.10.14/style.json build/coast > index.html
// The image tiles, the place lists and the archives are named for their contents, not the
// version (decisions/014, 018), so the style is the only record of which belong to it; this
// page reads them from there. What each place list holds, its licence and its count of
// places, it reads from the lists in the region's build, the same files publish.sh uploads.
// It shows the version's map (its viewer, one map wide), and a table of every name the map
// labels from our archives and every place in the lists, which it reads from names.tsv
// beside it (scripts/version_names.ts), so a release can be reviewed name by name.

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
  return `<li><p>${link(url)}</p><p>${escape(list.about)}. ${(list.places ?? list.features).length.toLocaleString('en')} ${list.features ? 'regions' : 'places'}. ` +
    `${escape(list.licence)}; credit “${escape(list.attribution)}”.</p></li>`;
});
const water: { mask?: string; grid?: string } | undefined = style.metadata?.['salishsea:water'];
const grid = water?.grid ? JSON.parse(readFileSync(`${src}/water-mask.json`, 'utf8')) : undefined;
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
  #map { display: block; width: 100%; height: 70vh; border: 1px solid var(--rule); margin: .75rem 0; }
  .filters { display: flex; flex-wrap: wrap; gap: .5rem; align-items: center; margin: .5rem 0; }
  .filters input { flex: 1 1 14rem; font: inherit; padding: .3rem .5rem; } .filters select { font: inherit; padding: .3rem; }
  #names { font-size: .9rem; } #names tbody tr { cursor: pointer; } #names tbody tr:hover, #names tbody tr.here { background: var(--rule); }
  #names td { padding-right: .75rem; } #names td:nth-child(5) { text-align: right; }
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
<iframe id="map" title="The map of version ${escape(version)}" src="viewer/index.html?picture&sightings=off"></iframe>

<h2>Names</h2>
<p>Every name the map labels from our own archives, by the layer it is drawn from, and every place in the search lists below (<code>list:</code>), with the zoom each is first drawn at, or for a list, the zoom it says to look from. Protomaps' own labels, of streets, towns and the like, aren't here. Choose a name to see it on the map above. All of them, with a link to the map at each, are in ${link(`${base}/names.tsv`)}, tab-separated.</p>
<div class="filters">
<input id="filter" type="search" placeholder="Filter by name" aria-label="Filter by name">
<select id="layer" aria-label="Layer"><option value="">Every layer</option></select>
<span id="count" class="muted" aria-live="polite">Loading…</span>
</div>
<table id="names"><thead><tr><th scope="col">Name</th><th scope="col">Kind</th><th scope="col">Near</th><th scope="col">Layer</th><th scope="col">Zoom</th><th scope="col">Details</th></tr></thead><tbody></tbody></table>
<script type="module">
// Up to this many rows are shown at once; the filter narrows the rest.
const SHOWN = 300;
const fold = (s) => s.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase();
const text = await (await fetch('names.tsv')).text();
const [header, ...lines] = text.trimEnd().split('\\n');
const columns = header.split('\\t');
const names = lines.map((line) => {
  const cells = line.split('\\t');
  const row = Object.fromEntries(columns.map((c, i) => [c, cells[i] ?? '']));
  row.search = fold(\`\${row.name} \${row.other_names}\`);
  return row;
});
const layer = document.getElementById('layer');
for (const l of [...new Set(names.map((n) => n.layer))].sort()) layer.append(new Option(l, l));
const filter = document.getElementById('filter');
const body = document.querySelector('#names tbody');
const count = document.getElementById('count');
const map = document.getElementById('map');
const show = () => {
  const words = fold(filter.value).split(/\\s+/).filter(Boolean);
  // Nothing is listed until something is typed: the whole table is tens of thousands of names.
  if (!words.length) {
    count.textContent = \`Type part of a name to find it among \${names.length.toLocaleString('en')}\`;
    body.replaceChildren();
    return;
  }
  const matching = names.filter((n) => (!layer.value || n.layer === layer.value) && words.every((w) => n.search.includes(w)));
  count.textContent = matching.length > SHOWN
    ? \`\${matching.length.toLocaleString('en')} names; the first \${SHOWN} shown\`
    : \`\${matching.length.toLocaleString('en')} names\`;
  body.replaceChildren(...matching.slice(0, SHOWN).map((n) => {
    const tr = document.createElement('tr');
    tr.tabIndex = 0;
    const details = [n.details, n.other_names && \`also \${n.other_names}\`].filter(Boolean).join('; ');
    for (const value of [n.name, n.kind, n.near, n.layer, n.zoom, details]) tr.insertCell().textContent = value;
    const go = () => {
      // The viewer keeps its place after the #, as zoom/latitude/longitude, and follows it.
      map.contentWindow.location.hash = \`\${n.zoom}/\${n.lat}/\${n.lon}\`;
      body.querySelector('.here')?.classList.remove('here');
      tr.classList.add('here');
      map.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    };
    tr.addEventListener('click', go);
    tr.addEventListener('keydown', (e) => { if (e.key === 'Enter') go(); });
    return tr;
  }));
};
filter.addEventListener('input', show);
layer.addEventListener('change', show);
show();
</script>
${images ? `
<h2>Image tiles</h2>
<p>For stitching into a picture rather than drawing a map: 256-pixel tiles, each drawn at 512 pixels, without labels. Put a tile's zoom and position in place of <code>{z}</code>, <code>{x}</code> and <code>{y}</code>.</p>
<p><code>${escape(images)}</code></p>
<p>They cover only some of the map at the closer zooms, so the tiles there are listed, one <code>z x y</code> to a line: ${link(images.replace('{z}/{x}/{y}.webp', 'tiles.txt'))}</p>
` : ''}${lists.length ? `
<h2>Place names</h2>
<p>For a search that takes people to a place on the map, the place lists give their places as rows of their <code>columns</code>: the name, its kind, a longitude and latitude to look at, a zoom to look from (MapLibre's), and any other names it goes by. The water regions' list is GeoJSON instead, its <code>features</code> the regions, each with its <code>name</code> as a card would say it and its <code>base</code> name as the map labels it (decision 027).</p>
<ul>
${lists.join('\n')}
</ul>
` : ''}${water?.mask && water.grid && grid ? `
<h2>Water mask</h2>
<p>The sea as a grid of ${grid.width.toLocaleString('en')} by ${grid.height.toLocaleString('en')} cells, for telling water from land: a 1-bit PNG, white where there is water, its rows from north to south. The JSON beside it gives the box it covers and the size of a cell (decision 028).</p>
<ul>
<li><p>${link(water.mask)}</p><p>${link(water.grid)}</p><p>${escape(grid.about)} ${escape(grid.licence)}; credit “${escape(grid.attribution)}”.</p></li>
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
