// The water regions (decisions/027) as a list a site can read, beside the place lists: a
// GeoJSON FeatureCollection, with its licence, from the build's one region per line.
//   node scripts/regions_list.ts build/coast/regions.geojsons build/coast/places-regions.json
import { readFileSync, writeFileSync } from 'node:fs';

const [from, to] = process.argv.slice(2);
if (!from || !to) throw new Error('usage: regions_list.ts REGIONS.geojsons OUT.json');
const features = readFileSync(from, 'utf8').split('\n').filter(Boolean).map((line) => JSON.parse(line));
writeFileSync(to, JSON.stringify({
  type: 'FeatureCollection',
  // Drawn from OpenStreetMap's land and told apart by its islands and towns (decisions/027).
  license: 'ODbL 1.0; © OpenStreetMap contributors; with USGS GNIS, Natural Resources Canada (Open Government Licence – Canada) and NOAA',
  features,
}));
