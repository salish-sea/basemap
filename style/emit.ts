// Writes the style as JSON for archives at a given address, for maps that load a style
// by URL rather than building it in code:
//   node style/emit.ts https://tiles.salishsea.io/2026.10.1/ > style.json

import { basemapStyle } from './style.ts';

const base = process.argv[2];
if (!base || !base.endsWith('/')) {
  console.error('usage: node style/emit.ts <base URL ending in />');
  process.exit(2);
}
process.stdout.write(JSON.stringify(basemapStyle({ base }), null, 1) + '\n');
