// The water regions (decisions/027) as a list a site can read, beside the place lists: a
// GeoJSON FeatureCollection, with its licence, from the build's one region per line.
//   node scripts/regions_list.ts build/coast/regions.geojsons build/coast/places-regions.json
import { readFileSync, writeFileSync } from 'node:fs';

const [from, to] = process.argv.slice(2);
if (!from || !to) throw new Error('usage: regions_list.ts REGIONS.geojsons OUT.json');
const features = readFileSync(from, 'utf8').split('\n').filter(Boolean).map((line) => JSON.parse(line));
// Described as the place lists are (decisions/018), so a version's index page can list it beside them.
writeFileSync(to, JSON.stringify({
  type: 'FeatureCollection',
  about: "The water regions: one for each water name the map labels, together covering the water from 42°N to 51.5°N, each with its name as a card would say it",
  // From government data only, nothing from OpenStreetMap (decisions/027).
  licence: 'Public domain in the US; Canadian names and outlines under the Open Government Licence – Canada; British Columbia\'s land under the Open Government Licence – British Columbia',
  attribution: 'Contains information licensed under the Open Government Licence – Canada and the Open Government Licence – British Columbia',
  features,
}));
