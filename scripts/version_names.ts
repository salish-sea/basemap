// Writes every name a version's map labels from our own archives, and every place in its
// search lists, as a table to read through when reviewing a release:
//   node scripts/version_names.ts build/coast https://tiles.salishsea.io/2026.11.4/viewer/index.html > names.tsv
// One row a name, tab-separated, with a header row. `layer` says where the name comes from:
// a layer of the landmarks, marine, osm or routes archive, or `list:` and a search list
// (decisions/018). `zoom` is MapLibre's zoom the name is first drawn at, or for a list, the zoom
// it says to look from; `map` opens the version's map there. Protomaps' own labels, of
// streets, towns and the like, aren't ours and aren't listed.

import { readFileSync } from 'node:fs';

const [src, viewer] = process.argv.slice(2);
if (!src || !viewer) {
  console.error('usage: node scripts/version_names.ts BUILD_DIR VIEWER_URL');
  process.exit(2);
}

type Geometry = { type: string; coordinates: unknown };
type Feature = { properties: Record<string, unknown>; geometry: Geometry; tippecanoe?: { minzoom?: number; layer?: string } };
interface Row { layer: string; name: string; kind: string; zoom: number; lon: number; lat: number; other: string[]; details: string }

const COLUMNS = ['layer', 'name', 'kind', 'zoom', 'lon', 'lat', 'other_names', 'details', 'map'];

/** The features of a file of GeoJSON features, one a line, as tippecanoe reads them. */
function features(file: string): Feature[] {
  return readFileSync(`${src}/${file}`, 'utf8').split('\n')
    .map((line) => line.replace(/^\x1e/, '').trim()).filter(Boolean).map((line) => JSON.parse(line));
}

/** A point to show a feature at: a point's own place, or the middle of the box around a line or shape. */
function at(geometry: Geometry): [number, number] {
  if (geometry.type === 'Point') return geometry.coordinates as [number, number];
  let [w, s, e, n] = [Infinity, Infinity, -Infinity, -Infinity];
  const walk = (c: unknown): void => {
    if (typeof (c as number[])[0] === 'number') {
      const [x, y] = c as number[];
      [w, s, e, n] = [Math.min(w, x), Math.min(s, y), Math.max(e, x), Math.max(y, n)];
    } else (c as unknown[]).forEach(walk);
  };
  walk(geometry.coordinates);
  return [(w + e) / 2, (s + n) / 2];
}

/** The zoom a feature is first drawn at: its own, else tippecanoe's, but never before its layer's. */
function zoomOf(f: Feature, layerMin = 0): number {
  const own = f.properties.min_zoom ?? f.properties.minzoom ?? f.tippecanoe?.minzoom ?? 0;
  return Math.max(Number(own), layerMin);
}

const rows: Row[] = [];
const add = (layer: string, f: Feature, kind: string, details = '', layerMin = 0) => {
  const name = f.properties.name;
  if (typeof name !== 'string' || !name) return;
  const [lon, lat] = at(f.geometry);
  const other = Array.isArray(f.properties.other_names) ? (f.properties.other_names as string[]) : [];
  rows.push({ layer, name, kind, zoom: zoomOf(f, layerMin), lon, lat, other, details });
};

// The marine archive's names of water and of points on it (style.ts, point_names and water_names).
for (const f of features('names.geojsons')) add('marine:names', f, String(f.properties.kind ?? ''));
// The landmarks archive: lighthouses, towers and landmarks; islets; peninsulas; parks; salmon runs.
for (const f of features('landmarks.geojsons')) {
  const height = Number(f.properties.height);
  add('landmarks:landmarks', f, String(f.properties.kind ?? ''), height ? `${height} m tall` : '');
}
for (const f of features('islets.geojsons')) add('landmarks:islets', f, 'islet');
for (const f of features('peninsulas.geojsons')) add('landmarks:peninsulas', f, 'peninsula');
for (const f of features('parks.geojsons')) {
  add('landmarks:parks', f, String(f.properties.kind ?? ''), f.properties.shore ? 'on the shore' : '');
}
for (const f of features('salmon.geojsons')) add('landmarks:salmon', f, 'river', String(f.properties.runs ?? ''));
// Ferry routes, named along their lines from zoom 11 (style.ts, ferry_labels), and the shipping
// lanes' names from zoom 12 (route_names).
for (const f of features('ferry_routes.geojsons')) add('osm:ferry_routes', f, 'ferry route', String(f.properties.network ?? ''), 11);
for (const f of features('routes.geojsons')) if (f.properties.kind === 'name') add('routes:marks', f, 'shipping lane', '', 12);

// The search lists, as SalishSea.io's search reads them.
for (const list of ['gazetteers', 'osm', 'parks']) {
  const { columns, places } = JSON.parse(readFileSync(`${src}/places-${list}.json`, 'utf8')) as { columns: string[]; places: unknown[][] };
  const col = (name: string) => columns.indexOf(name);
  for (const p of places) {
    rows.push({
      layer: `list:${list}`, name: String(p[col('name')]), kind: String(p[col('kind')]), zoom: Number(p[col('zoom')]),
      lon: Number(p[col('lon')]), lat: Number(p[col('lat')]), other: (p[col('other_names')] as string[]) ?? [], details: '',
    });
  }
}
// The water regions, which no layer draws but cards name (decisions/027).
const regions = JSON.parse(readFileSync(`${src}/places-regions.json`, 'utf8')) as { features: Feature[] };
for (const f of regions.features) {
  const base = String(f.properties.base ?? '');
  add('list:regions', f, 'water region', base && base !== f.properties.name ? `labelled ${base}` : '');
}

// A tab or line break would split a cell, so each is a space.
const cell = (v: string) => v.replace(/[\t\r\n]+/g, ' ');
const round = (v: number) => String(Math.round(v * 1e5) / 1e5);
rows.sort((a, b) => a.name.localeCompare(b.name, 'en') || a.layer.localeCompare(b.layer));
const out = [COLUMNS.join('\t')];
for (const r of rows) {
  // The viewer keeps its place after the #, as zoom/latitude/longitude.
  const map = `${viewer}?picture&sightings=off#${r.zoom}/${round(r.lat)}/${round(r.lon)}`;
  out.push([r.layer, r.name, r.kind, String(r.zoom), round(r.lon), round(r.lat), r.other.join('; '), r.details, map].map(cell).join('\t'));
}
process.stdout.write(out.join('\n') + '\n');
console.error(`${rows.length} names`);
