// Draws the README's pictures from a build, so they show the map as it is built rather
// than as it looked when someone last took a screenshot:
//   make pictures REGION=coast        from this machine's build of a region
//   make pictures VERSION=2026.10.3   from a published version, which is the whole coast
// Each view is drawn by the comparison page in its picture mode, in headless Chromium,
// and written to docs/images/ as WebP, which keeps the text sharp at a third the size of
// a squeezed PNG, so redrawing them adds little to the repository's history. A view outside
// the region is skipped, and its old picture kept.

import { execFileSync } from 'node:child_process';
import { existsSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { chromium } from 'playwright';
import { createServer } from 'vite';

const arg = process.argv[2] ?? 'window';
// A published version is drawn by its own comparison page, from tiles.salishsea.io.
const version = /^\d{4}\.\d{2}\.\d+$/.test(arg) ? arg : null;
const region = version ? 'coast' : arg;
// West, south, east, north; as in the Makefile.
const BOUNDS: Record<string, [number, number, number, number]> = {
  window: [-124.0, 48.0, -122.2, 49.2],
  coast: [-136.0, 36.0, -120.0, 54.8],
};

interface View {
  file: string;
  /** `#zoom/lat/lon`, as the comparison page writes it. */
  at: string;
  /** In CSS pixels; the picture is drawn at twice that, for high-density screens. */
  size: [number, number];
  sightings?: boolean;
  /** The area the view shows, west, south, east, north, which the region must cover. */
  needs: [number, number, number, number];
}

const VIEWS: View[] = [
  { file: 'overview.webp', at: '9.4/48.56/-123.05', size: [1000, 700], sightings: true, needs: [-123.6, 48.3, -122.5, 48.8] },
  { file: 'zoom14.webp', at: '14/48.5157/-123.145', size: [1000, 700], needs: [-123.17, 48.5, -123.12, 48.53] },
  { file: 'rivers.webp', at: '10/48.40/-122.28', size: [1000, 700], needs: [-122.63, 48.25, -121.93, 48.55] },
  // Haro Strait's two-way route and the lanes off Victoria, with their arrows (decisions/019).
  { file: 'lanes.webp', at: '10.6/48.37/-123.13', size: [1000, 700], sightings: true, needs: [-123.45, 48.22, -122.8, 48.52] },
  // The whole range, which at z5.15 fills the picture.
  { file: 'coast.webp', at: '5.15/46.22/-128.0', size: [810, 1370], needs: [-136.0, 36.0, -120.0, 54.8] },
];

const bounds = BOUNDS[region];
if (!bounds || (!version && !existsSync(`build/${region}/protomaps.pmtiles`))) {
  console.error(`no build for ${region}; run make REGION=${region} first`);
  process.exit(1);
}
const covers = ([w, s, e, n]: View['needs']) => w >= bounds[0] && s >= bounds[1] && e <= bounds[2] && n <= bounds[3];

const server = version ? null : await createServer({ root: 'viewer', configFile: 'viewer/vite.config.ts', server: { port: 5180, strictPort: false }, logLevel: 'warn' });
await server?.listen();
const origin = server ? server.resolvedUrls!.local[0] : `https://tiles.salishsea.io/${version}/viewer/index.html`;
// Screenshots go here before they are converted, so a failure leaves nothing in docs/.
const scratch = mkdtempSync(join(tmpdir(), 'basemap-pictures-'));
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
try {
  for (const view of VIEWS) {
    if (!covers(view.needs)) {
      console.log(`${view.file}: outside ${region}, kept as it was`);
      continue;
    }
    const page = await browser.newPage({ viewport: { width: view.size[0], height: view.size[1] }, deviceScaleFactor: 2 });
    const query = new URLSearchParams({ ...(version ? {} : { base: `/${region}/` }), picture: '', sightings: view.sightings ? 'on' : 'off' });
    await page.goto(`${origin}?${query}#${view.at}`);
    // Waits until every tile in view is drawn: `idle` fires once nothing is loading or
    // fading, and a repaint makes sure it fires even if the map is idle already.
    await page.waitForFunction(() => 'maps' in window, null, { timeout: 30_000 });
    await page.evaluate(() => new Promise<void>((done) => {
      const map = (window as unknown as { maps: { left: import('maplibre-gl').Map } }).maps.left;
      map.once('idle', () => done());
      map.triggerRepaint();
    }));
    const raw = join(scratch, `${view.file}.png`);
    await page.screenshot({ path: raw });
    await page.close();
    execFileSync('cwebp', ['-quiet', '-q', '85', '-m', '6', raw, '-o', `docs/images/${view.file}`]);
    console.log(`${view.file}: drawn`);
  }
} finally {
  rmSync(scratch, { recursive: true, force: true });
  await browser.close();
  await server?.close();
}
