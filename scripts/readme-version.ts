// Points the README at one published version; scripts/release.sh runs it after a publish:
//   node scripts/readme-version.ts 2026.10.13
// It reads the version's style from tiles.salishsea.io and rewrites the README's list of
// that version's files, between the `newest-version` comments, with the URLs the style
// names in its metadata: the image tiles (decisions/014) and the lists of place names
// (decisions/018). Those are named for their contents, not the version, so they can't be
// guessed from the version number. It also moves the README's other versioned URLs, such
// as the example's style, to the version. Commit the result.

import { readFileSync, writeFileSync } from 'node:fs';

const version = process.argv[2];
if (!version || !/^\d{4}\.(0[1-9]|1[0-2])\.[1-9]\d*$/.test(version)) {
  console.error('usage: node scripts/readme-version.ts YYYY.MM.N');
  process.exit(2);
}
const base = `https://tiles.salishsea.io/${version}`;
const response = await fetch(`${base}/style.json`);
if (!response.ok) {
  console.error(`${base}/style.json answered ${response.status}; is ${version} published?`);
  process.exit(1);
}
const metadata = (await response.json()).metadata ?? {};
const images: unknown = metadata['salishsea:images'];
const places: unknown = metadata['salishsea:places'];
if (typeof images !== 'string' || !places || typeof places !== 'object') {
  console.error(`version ${version}'s style names no image tiles or no lists of places`);
  process.exit(1);
}

/** What each list holds, by the name the style gives it. A list added later is shown by its name. */
const LISTS: Record<string, string> = {
  gazetteers: 'Place names of water bodies and points, from the US and Canadian gazetteers',
  osm: 'Place names of islands, cities, towns, villages and ferry terminals, from OpenStreetMap, under the ODbL',
};
// Versions published before index pages were (decisions/007) have none.
const index = (await fetch(`${base}/index.html`, { method: 'HEAD' })).ok;
const lines = [
  `The newest version is **${version}**:`,
  '',
  ...(index ? [`- A page linking every file of the version: ${base}/index.html`] : []),
  `- Style: ${base}/style.json`,
  `- A page for trying it out beside Esri's map: ${base}/viewer/index.html`,
  `- Image tiles, for stitching into a picture: \`${images}\``,
  ...Object.entries(places).map(([name, url]) => `- ${LISTS[name] ?? `Place names, \`${name}\``}: ${url}`),
];

const file = 'README.md';
const readme = readFileSync(file, 'utf8');
const block = /(<!-- newest-version[^>]*-->)[\s\S]*?(<!-- \/newest-version -->)/;
if (!block.test(readme)) {
  console.error(`${file} has no newest-version comments to write between`);
  process.exit(1);
}
const updated = readme
  .replace(block, (_, start: string, end: string) => [start, ...lines, end].join('\n'))
  .replaceAll(/https:\/\/tiles\.salishsea\.io\/\d{4}\.\d{2}\.\d+\//g, `${base}/`);
writeFileSync(file, updated);
console.log(`${file} now names ${version}`);
