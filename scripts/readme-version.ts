// Points the README at one published version; scripts/release.sh runs it after a publish:
//   node scripts/readme-version.ts 2026.10.13
// It checks that the version's style and index page are on tiles.salishsea.io, and rewrites the
// README's lines between the `newest-version` comments to link them; the index page links the
// rest of the version's files. It also moves the README's other versioned URLs, such as the
// example's style, to the version. Commit the result.

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
// Every version since 2026.10.14 has an index page (decisions/007), which links all of its files.
const index = (await fetch(`${base}/index.html`, { method: 'HEAD' })).ok;
if (!index) {
  console.error(`${base}/index.html isn't there; has ${version} finished publishing?`);
  process.exit(1);
}
const lines = [
  `The newest version is **${version}**.`,
  '',
  `- Its index page shows the map and every name it labels, and links every file it is made of: ${base}/index.html`,
  `- Its style, for a MapLibre map: ${base}/style.json`,
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
