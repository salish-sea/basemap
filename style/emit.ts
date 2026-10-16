// Writes the style as JSON, for maps that load a style by URL rather than building it in
// code. The archives are at <base><archive>.pmtiles, unless an argument gives one's URL:
//   node style/emit.ts https://tiles.salishsea.io/archives/ protomaps=https://…/protomaps-3f9a….pmtiles … > style.json
// An `images=` argument gives the URL of the build's image tiles (decisions/014), with
// {z}, {x} and {y} in it, which the style carries in its metadata as `salishsea:images`;
// `landmark-icons=` the URL of the landmarks' sprite, without its extension (decisions/015);
// `glyphs=` the URL of the labels' fonts, ending in a slash (decisions/017); and
// `places-<list>=` the URL of a list of the names the map labels, which the style carries
// in its metadata under `salishsea:places`, by the list's name (decisions/018).

import { ARCHIVES, basemapStyle, OVERVIEW_ARCHIVES, type Archive } from './style.ts';

const [base, ...given] = process.argv.slice(2);
const archives: Partial<Record<Archive, string>> = {};
let images: string | undefined;
let landmarkIcons: string | undefined;
let glyphs: string | undefined;
const places: Record<string, string> = {};
for (const arg of given) {
  const [name, url] = arg.split(/=(.*)/s);
  if (name === 'images' && url?.includes('{z}')) {
    images = url;
    continue;
  }
  if (name === 'landmark-icons' && url) {
    landmarkIcons = url;
    continue;
  }
  const list = name?.match(/^places-([a-z]+)$/)?.[1];
  if (list && url?.endsWith('.json')) {
    places[list] = url;
    continue;
  }
  if (name === 'glyphs' && url?.endsWith('/')) {
    glyphs = url;
    continue;
  }
  if (!ARCHIVES.includes(name as Archive) || !url) {
    console.error(`not an archive=URL argument: ${arg}`);
    process.exit(2);
  }
  archives[name as Archive] = url;
}
if (!landmarkIcons) {
  console.error('a published style needs landmark-icons=URL: without it the sprite is a path on this site');
  process.exit(2);
}
if (!glyphs) {
  console.error("a published style needs glyphs=URL/: Protomaps' fonts alone have no glyphs for the depth labels");
  process.exit(2);
}
if (!base || !base.endsWith('/')) {
  console.error('usage: node style/emit.ts <base URL ending in /> [archive=URL ...]');
  process.exit(2);
}
// A build has the zoomed-out map if it was given its archives (decisions/012).
const overview = OVERVIEW_ARCHIVES.every((a) => a in archives);
const style = basemapStyle({ base, archives, overview, landmarkIcons, glyphs });
if (images) style.metadata = { ...(style.metadata as object | undefined), 'salishsea:images': images };
if (Object.keys(places).length) style.metadata = { ...(style.metadata as object | undefined), 'salishsea:places': places };
process.stdout.write(JSON.stringify(style, null, 1) + '\n');
