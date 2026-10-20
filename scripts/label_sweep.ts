// Finds labels that appear as the map is zoomed in and then disappear while their place is
// still on the screen, which a picture at one zoom can't show:
//   node scripts/label_sweep.ts 2026.10.16 labels.geojsons [--landmarks=landmarks.pmtiles]
// For each point in labels.geojsons (one GeoJSON feature a line, with `name` and
// `min_zoom`, as build/<region>/salmon.geojsons is), the comparison page, built against the
// published version's archives, is centred on it and stepped from its first zoom to 15; at
// each step MapLibre is asked which of the salmon runs' labels it drew there. A label drawn
// and then not drawn has lost its place to another label. --landmarks puts a local build of
// the landmarks' archive, which holds the islets' names and the rivers' runs, in place of the
// version's, to sweep a change before it is published.

import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { createServer } from 'node:http';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { chromium } from 'playwright';

const [version, labelsPath] = process.argv.slice(2).filter((a) => !a.startsWith('--'));
const landmarks = process.argv.find((a) => a.startsWith('--landmarks='))?.slice('--landmarks='.length);
if (!version || !/^\d{4}\.\d{2}\.\d+$/.test(version) || !labelsPath) {
  console.error('usage: node scripts/label_sweep.ts VERSION labels.geojsons [--landmarks=landmarks.pmtiles]');
  process.exit(2);
}
const LAYER = 'salmon_runs';
const LAST_ZOOM = 15;

interface Label { name: string; lon: number; lat: number; minzoom: number }
const labels: Label[] = readFileSync(labelsPath, 'utf8').split('\n').map((l) => l.replace(/^\x1e/, '').trim()).filter(Boolean).map((l) => {
  const f = JSON.parse(l);
  const [lon, lat] = Array.isArray(f.geometry.coordinates[0]) ? f.geometry.coordinates[0] : f.geometry.coordinates;
  return { name: f.properties.name, lon, lat, minzoom: Number(f.properties.min_zoom ?? 10) };
});

// The comparison page, built as publish.sh builds it, against the version's archives.
const style = await (await fetch(`https://tiles.salishsea.io/${version}/style.json`)).json();
const archives = Object.fromEntries(Object.entries(style.sources as Record<string, { url?: string }>)
  .filter(([, s]) => s.url?.startsWith('pmtiles://')).map(([name, s]) => [name, s.url!.slice('pmtiles://'.length)]));
const sprite = (style.sprite as { id: string; url: string }[]).find((s) => s.id === 'landmarks')!.url;
const out = mkdtempSync(join(tmpdir(), 'label-sweep-'));
execFileSync('pnpm', ['exec', 'vite', 'build', 'viewer', '--outDir', out, '--emptyOutDir', '--logLevel', 'warn'], {
  stdio: 'inherit',
  env: { ...process.env, VITE_TILES_ARCHIVES: JSON.stringify(archives), VITE_LANDMARK_ICONS: sprite, VITE_GLYPHS: style.glyphs.replace('{fontstack}/{range}.pbf', '') },
});
const local = landmarks ? readFileSync(landmarks) : null;

// The built page, from its folder: by a server, not by intercepting requests, because
// MapLibre's worker loads scripts the page's interception doesn't see.
const server = createServer((request, response) => {
  const path = new URL(request.url ?? '/', 'http://localhost').pathname.replace(/^\//, '') || 'index.html';
  try {
    const type = /\.m?js$/.test(path) ? 'text/javascript' : path.endsWith('.css') ? 'text/css' : 'text/html';
    response.writeHead(200, { 'content-type': type }).end(readFileSync(join(out, path)));
  } catch {
    response.writeHead(404).end();
  }
});
await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
const origin = `http://127.0.0.1:${(server.address() as { port: number }).port}`;

const browser = await chromium.launch();
const vanished: string[] = [];
try {
  const page = await browser.newPage({ viewport: { width: 1000, height: 700 } });
  // A local landmarks' archive in place of the version's, in the byte ranges PMTiles asks for.
  if (local) {
    await page.route(archives.landmarks, async (route) => {
      const m = /bytes=(\d+)-(\d*)/.exec(route.request().headers()['range'] ?? '');
      const start = m ? Number(m[1]) : 0;
      const end = m && m[2] ? Math.min(Number(m[2]), local.length - 1) : local.length - 1;
      await route.fulfill({
        status: m ? 206 : 200, body: local.subarray(start, end + 1),
        headers: { 'content-type': 'application/octet-stream', 'access-control-allow-origin': '*', 'content-range': `bytes ${start}-${end}/${local.length}` },
      });
    });
  }
  if (process.env.SWEEP_DEBUG) page.on('console', (m) => console.log('page:', m.text())).on('pageerror', (e) => console.log('error:', e.message)).on('requestfailed', (r) => console.log('failed:', r.url()));
  await page.goto(`${origin}/index.html?picture&sightings=off`);
  await page.waitForFunction(() => (window as unknown as { basemap?: { loaded(): boolean } }).basemap?.loaded());
  for (const label of labels) {
    const drawn: number[] = [];
    for (let zoom = label.minzoom; zoom <= LAST_ZOOM; zoom++) {
      const shown = await page.evaluate(async ({ label, zoom, layer }) => {
        const map = (window as unknown as { basemap: any }).basemap;
        map.jumpTo({ center: [label.lon, label.lat], zoom });
        await new Promise((resolve) => map.once('idle', resolve));
        return map.queryRenderedFeatures({ layers: [layer] }).some((f: any) => f.properties.name === label.name);
      }, { label, zoom, layer: LAYER });
      if (shown) drawn.push(zoom);
      else if (drawn.length) {
        vanished.push(`${label.name} (${label.lon.toFixed(3)}, ${label.lat.toFixed(3)}): drawn at ${drawn.join(', ')}, not at ${zoom}`);
        break;
      }
    }
    if (!drawn.length) vanished.push(`${label.name} (${label.lon.toFixed(3)}, ${label.lat.toFixed(3)}): never drawn from ${label.minzoom} to ${LAST_ZOOM}`);
  }
} finally {
  await browser.close();
  server.close();
  rmSync(out, { recursive: true, force: true });
}
console.log(`${labels.length} labels swept${landmarks ? ` with ${landmarks}` : ''} on ${version}`);
for (const line of vanished) console.log(`  ${line}`);
if (!vanished.length) console.log('  none appeared and then disappeared');
