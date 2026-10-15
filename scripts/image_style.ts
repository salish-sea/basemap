// Writes the style the image tiles are drawn from, for one region, so the Makefile can tell
// whether a change to style/style.ts changes the tiles: a change to the labels, which the
// tiles leave out, leaves this the same, and the tiles aren't drawn again (decisions/014).
//   node scripts/image_style.ts REGION > build/REGION/images-style.json

import { imageStyle } from '../style/style.ts';

const region = process.argv[2];
if (!region) {
  console.error('usage: node scripts/image_style.ts REGION');
  process.exit(2);
}
// As viewer/images.ts builds it, but at a fixed address: only what it draws matters here.
const style = imageStyle({ base: `http://localhost/${region}/`, assets: 'http://localhost/assets/', overview: region !== 'window' });
process.stdout.write(JSON.stringify(style, null, 1) + '\n');
