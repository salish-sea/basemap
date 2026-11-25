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
/** What each archive holds, by the name of the style's source. One added later is shown by its name alone. */
const ARCHIVES: Record<string, string> = {
  protomaps: "Protomaps' map of OpenStreetMap: land, roads, places and the water's outlines",
  osm: 'Our own layers from OpenStreetMap: ferry routes and nature reserves',
  depth: 'Depth: the bands, the depth contours and the ground that dries at low tide',
  elevation: 'Heights of the land and the seafloor, which the browser shades as the relief',
  marine: 'Names of bodies of water and points, and the Canada–US boundary at sea',
  landmarks: 'Landmarks, and the names of islets, peninsulas and parks, and the salmon runs',
  routes: 'Shipping lanes and the other routes ships keep to',
  regions: 'The water regions, hidden unless a page shows them',
  overview: 'The coarse map of the whole Northeast Pacific, shown zoomed out and past the coast',
  overview_elevation: "The coarse map's heights, for its relief",
};
const archives = Object.entries(style.sources as Record<string, { url?: string }>)
  .filter(([, source]) => source.url?.startsWith('pmtiles://'))
  .map(([name, source]) => row(`<code>${escape(name)}</code>`,
    `${ARCHIVES[name] ? `${escape(ARCHIVES[name])}<br>` : ''}${link(source.url!.slice('pmtiles://'.length))}`));
// The image tiles' deepest zoom, from the list of them in the build, which publish.sh uploads as tiles.txt.
const imageZooms = images ? readFileSync(`${src}/images.txt`, 'utf8').split('\n').filter(Boolean).map((line) => Number(line.split(' ')[0])) : [];
const deepest = imageZooms.length ? Math.max(...imageZooms) : undefined;
const decision = (n: string, file: string) => `<a href="${repo}/blob/${escape(version)}/decisions/${file}">decision ${n}</a>`;

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
<p>This page shows version ${escape(version)} of the basemap, links every file it is made of, and lets you look up every name its map labels. None of the files ever changes, so a site can link them and cache them for a year. How to use them is in the <a href="${repo}#readme">README</a>; the version was built from the commit tagged <a href="${repo}/tree/${escape(version)}">${escape(version)}</a>.</p>
<p class="muted">On this page: <a href="#map">the map</a> · <a href="#names-heading">names</a> · <a href="#image-tiles">image tiles</a> · <a href="#place-lists">place lists</a> · <a href="#water-mask">water mask</a> · <a href="#archives">tile archives</a></p>

<h2>The map</h2>
<table><tbody>
${row('Style', link(`${base}/style.json`))}
${row('Comparison page, the map beside the same map without its relief', link(`${base}/viewer/index.html`))}
</tbody></table>
<iframe id="map" title="The map of version ${escape(version)}" src="viewer/index.html?picture&sightings=off"></iframe>

<h2 id="names-heading">Names</h2>
<p>Look up any name the map labels, or any place in the place lists below. Each row says where the name is, the layer it is drawn from, and the zoom it first appears at; for a place from a list, whose layer starts <code>list:</code>, the zoom is the one the list says to view it from. Choose a row to see it on the map. Labels from Protomaps' own map, such as streets and most towns, aren't here.</p>
<p>The whole table is also in ${link(`${base}/names.tsv`)}, tab-separated for a spreadsheet, with a link to the map at each name.</p>
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
const response = await fetch('names.tsv');
if (!response.ok) {
  document.getElementById('count').textContent = \`names.tsv could not be loaded (\${response.status})\`;
  throw new Error(\`names.tsv: \${response.status}\`);
}
const text = await response.text();
// A cell names.tsv quotes, because it starts with a quote mark or a formula's first character.
const unquote = (c) => (c.startsWith('"') && c.endsWith('"') && c.length > 1 ? c.slice(1, -1).replaceAll('""', '"') : c);
const [header, ...lines] = text.trimEnd().split('\\n');
const columns = header.split('\\t');
const names = lines.map((line) => {
  const cells = line.split('\\t').map(unquote);
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
    ? \`\${matching.length.toLocaleString('en')} names; the first \${SHOWN} are shown, so type more to narrow them\`
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
<h2 id="image-tiles">Image tiles</h2>
<p>For stitching into a picture rather than drawing a map: the map without its labels, in 256-pixel tiles, each drawn at 512 pixels for high-density screens. Put a tile's zoom and position in place of <code>{z}</code>, <code>{x}</code> and <code>{y}</code> (${decision('014', '014-image-tiles-are-drawn-from-the-style-along-the-shore.md')}).</p>
<p>They are numbered as Esri's are, so image zoom 10 shows what a MapLibre map shows at zoom 9. They cover zooms 0 to 5 over the coarse map, 6 to 10 over the coast, and ${deepest && deepest > 10 ? `11 to ${deepest}` : 'the closer zooms'} only along the Salish Sea's shore.</p>
<p><code>${escape(images)}</code></p>
<p>Which tiles exist is listed, one <code>z x y</code> to a line; ask only for those: ${link(images.replace('{z}/{x}/{y}.webp', 'tiles.txt'))}</p>
` : ''}${lists.length ? `
<h2 id="place-lists">Place lists</h2>
<p>For a search that takes people to a place on the map. Each list is JSON: its <code>columns</code> names the fields, and each place is a row of them: the name, its kind, a longitude and latitude, a MapLibre zoom to view it from, and any other names it goes by. The <code>gazetteers</code> and <code>osm</code> lists are for search; <code>parks</code> is not, and a search shouldn't load it (${decision('018', '018-the-names-the-map-labels-are-published-as-lists.md')}).</p>
<p>The water regions' list is GeoJSON instead: each feature has a <code>name</code> to show a person, such as “Mud Bay (Sucia Island)” where several share a name, and a <code>base</code> name, as the map labels it (${decision('027', '027-every-water-name-has-a-region-and-the-regions-cover-the-water.md')}).</p>
<ul>
${lists.join('\n')}
</ul>
` : ''}${water?.mask && water.grid && grid ? `
<h2 id="water-mask">Water mask</h2>
<p>For measuring distance by sea rather than in a straight line: a 1-bit PNG of ${grid.width.toLocaleString('en')} by ${grid.height.toLocaleString('en')} cells, white where there is water, its rows from north to south. The JSON beside it gives the area it covers and the size of a cell. A search for a route across it must allow diagonal steps between cells; with only straight steps, narrow passages such as Dodd Narrows are closed (${decision('028', '028-the-water-mask-is-published.md')}).</p>
<ul>
<li><p>${link(water.mask)}</p><p>${link(water.grid)}</p><p>${escape(grid.about)} ${escape(grid.licence)}; credit “${escape(grid.attribution)}”.</p></li>
</ul>
` : ''}
<h2 id="archives">Tile archives</h2>
<p>The <a href="https://docs.protomaps.com/pmtiles/">PMTiles</a> archives of vector and elevation tiles that the style draws from, by the name of the style's source.</p>
<table><tbody>
${archives.join('\n')}
</tbody></table>
</body>
</html>
`);
