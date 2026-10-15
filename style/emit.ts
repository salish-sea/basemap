// Writes the style as JSON, for maps that load a style by URL rather than building it in
// code. The archives are at <base><archive>.pmtiles, unless an argument gives one's URL:
//   node style/emit.ts https://tiles.salishsea.io/archives/ protomaps=https://…/protomaps-3f9a….pmtiles … > style.json

import { ARCHIVES, basemapStyle, OVERVIEW_ARCHIVES, type Archive } from './style.ts';

const [base, ...given] = process.argv.slice(2);
const archives: Partial<Record<Archive, string>> = {};
for (const arg of given) {
  const [name, url] = arg.split(/=(.*)/s);
  if (!ARCHIVES.includes(name as Archive) || !url) {
    console.error(`not an archive=URL argument: ${arg}`);
    process.exit(2);
  }
  archives[name as Archive] = url;
}
if (!base || !base.endsWith('/')) {
  console.error('usage: node style/emit.ts <base URL ending in /> [archive=URL ...]');
  process.exit(2);
}
// A build has the zoomed-out map if it was given its archives (decisions/012).
const overview = OVERVIEW_ARCHIVES.every((a) => a in archives);
process.stdout.write(JSON.stringify(basemapStyle({ base, archives, overview }), null, 1) + '\n');
