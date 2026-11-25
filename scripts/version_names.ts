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

const COLUMNS = ['layer', 'name', 'kind', 'zoom', 'lon', 'lat', 'near', 'other_names', 'details', 'map'];
// A name farther than this from every listed town and island is too far from them to place by one.
const NEAR_KM = 40;

/** The features of a file of GeoJSON features, one a line, as tippecanoe reads them. */
function features(file: string): Feature[] {
  return readFileSync(`${src}/${file}`, 'utf8').split('\n')
    .map((line) => line.replace(/^\x1e/, '').trim()).filter(Boolean).map((line) => JSON.parse(line));
}

/** The box around a feature, as west, south, east and north. */
function box(geometry: Geometry): [number, number, number, number] {
  let [w, s, e, n] = [Infinity, Infinity, -Infinity, -Infinity];
  const walk = (c: unknown): void => {
    if (typeof (c as number[])[0] === 'number') {
      const [x, y] = c as number[];
      [w, s, e, n] = [Math.min(w, x), Math.min(s, y), Math.max(e, x), Math.max(y, n)];
    } else (c as unknown[]).forEach(walk);
  };
  walk(geometry.coordinates);
  return [w, s, e, n];
}

/** A point to show a feature at: a point's own place, or the middle of the box around a line or shape. */
function at(geometry: Geometry): [number, number] {
  if (geometry.type === 'Point') return geometry.coordinates as [number, number];
  const [w, s, e, n] = box(geometry);
  return [(w + e) / 2, (s + n) / 2];
}

/** MapLibre's zoom at which a shape about fills a map 600 pixels square, between 8 and 14. */
function fitting(geometry: Geometry): number {
  const [w, s, e, n] = box(geometry);
  const lat = ((s + n) / 2) * (Math.PI / 180);
  // In degrees of longitude, the larger of the box's width and its height.
  const span = Math.max(e - w, (n - s) / Math.cos(lat), 1e-6);
  return Math.min(14, Math.max(8, Math.floor(Math.log2((600 * 360) / (512 * span)))));
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
// The water regions, which no layer draws but cards name (decisions/027), each with the zoom
// at which it fits the map, since a region has no zoom of its own.
const regions = JSON.parse(readFileSync(`${src}/places-regions.json`, 'utf8')) as { features: Feature[] };
for (const f of regions.features) {
  const base = String(f.properties.base ?? '');
  add('list:regions', { ...f, properties: { ...f.properties, min_zoom: fitting(f.geometry) } }, 'water region',
    base && base !== f.properties.name ? `labelled ${base}` : '');
}

// Where each name is, to tell apart the many with one name (fifteen Mud Bays): the island the
// OpenStreetMap list says it is on, or the nearest of that list's cities, towns, villages and
// islands, as "3 km NE of Olympia", or both, as "on Vancouver Island, 4 km S of Ladysmith".
const round = (v: number) => String(Math.round(v * 1e5) / 1e5);
const osm = JSON.parse(readFileSync(`${src}/places-osm.json`, 'utf8')) as {
  columns: string[]; places: unknown[][]; gazetteer_islands?: { columns: string[]; rows: unknown[][] };
};
const oc = (name: string) => osm.columns.indexOf(name);
const towns = osm.places.filter((p) => ['city', 'town', 'village', 'island'].includes(String(p[oc('kind')])))
  .map((p) => ({ name: String(p[oc('name')]), island: p[oc('kind')] === 'island', lon: Number(p[oc('lon')]), lat: Number(p[oc('lat')]) }));
const islandOf = new Map<string, string>();
if (osm.gazetteer_islands) {
  const ic = (name: string) => osm.gazetteer_islands!.columns.indexOf(name);
  for (const r of osm.gazetteer_islands.rows) islandOf.set(`${r[ic('name')]}|${round(Number(r[ic('lon')]))}|${round(Number(r[ic('lat')]))}`, String(r[ic('island')]));
}
const COMPASS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
function near(r: Row): string {
  const island = islandOf.get(`${r.name}|${round(r.lon)}|${round(r.lat)}`);
  let best: { name: string; km: number; dx: number; dy: number } | undefined;
  // Once the island is known, a town on it or near it says more than another island.
  for (const t of island ? towns.filter((t) => !t.island) : towns) {
    // Kilometres east and north of the town, near enough for these distances.
    const dx = (r.lon - t.lon) * 111.32 * Math.cos((t.lat * Math.PI) / 180);
    const dy = (r.lat - t.lat) * 110.57;
    const km = Math.hypot(dx, dy);
    if (!best || km < best.km) best = { name: t.name, km, dx, dy };
  }
  const on = island ? `on ${island}` : '';
  if (!best || best.km > NEAR_KM || best.name === r.name) return on;
  const bearing = (Math.atan2(best.dx, best.dy) * 180) / Math.PI;
  const town = best.km < 1 ? `at ${best.name}` : `${Math.round(best.km)} km ${COMPASS[Math.round(((bearing + 360) % 360) / 45) % 8]} of ${best.name}`;
  return [on, town].filter(Boolean).join(', ');
}

// A tab or line break would split a cell, so each is a space.
const cell = (v: string) => v.replace(/[\t\r\n]+/g, ' ');
rows.sort((a, b) => a.name.localeCompare(b.name, 'en') || a.layer.localeCompare(b.layer));
const out = [COLUMNS.join('\t')];
for (const r of rows) {
  // The viewer keeps its place after the #, as zoom/latitude/longitude.
  const map = `${viewer}?picture&sightings=off#${r.zoom}/${round(r.lat)}/${round(r.lon)}`;
  out.push([r.layer, r.name, r.kind, String(r.zoom), round(r.lon), round(r.lat), near(r), r.other.join('; '), r.details, map].map(cell).join('\t'));
}
process.stdout.write(out.join('\n') + '\n');
console.error(`${rows.length} names`);
