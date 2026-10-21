// Draws the basemap's image tiles (decisions/014) for scripts/images.ts, which opens this
// page in headless Chromium and calls `drawBlock` for each block of tiles. A block is up to
// 4 by 4 tiles of 256 pixels, drawn at twice that for high-density screens, in the middle of
// a map a tile wider on every side, so the relief at a block's edge is shaded from the
// ground beyond it. The style is the map's without its labels and icons (imageStyle in
// style/style.ts).

import { addProtocol, Map, setWorkerUrl } from 'maplibre-gl';
import maplibreWorker from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';
import { PMTiles, Protocol, type Source } from 'pmtiles';
import { ASSETS_PATH, imageStyle } from '../style/style.ts';

setWorkerUrl(maplibreWorker);
// pmtiles unzips tiles with the browser's DecompressionStream when there is one. On the
// build machine, Chromium's fails on some tiles of under a hundred bytes that are sound
// gzip, which MapLibre reports as "Failed to fetch"; without it, pmtiles uses fflate.
delete (globalThis as { DecompressionStream?: unknown }).DecompressionStream;
const protocol = new Protocol();
addProtocol('pmtiles', protocol.tile);

const TILE = 256;
const BLOCK = 4;
const SCALE = 2;
const SIZE = 1280;

const params = new URLSearchParams(location.search);
const base = new URL(params.get('base') ?? '/window/', location.href).href;
const style = imageStyle({
  base,
  assets: new URL(`/${ASSETS_PATH}`, location.href).href,
  overview: !base.endsWith('/window/'),
});

// Chromium's HTTP cache sometimes answers a range it was asked for before with fewer bytes
// than it holds, or none. pmtiles then reports a cut-off tile as "unexpected EOF", but reads
// an empty one as a tile with nothing in it, which MapLibre draws as bare background without
// an error. So each archive is read afresh, and a short answer is a failure, which refuses
// the block. A small archive's first read asks for more than it has, as pmtiles always does.
const uncached = (url: string): Source => ({
  getKey: () => url,
  async getBytes(offset, length, signal) {
    const response = await fetch(url, { signal, cache: 'no-store', headers: { range: `bytes=${offset}-${offset + length - 1}` } });
    if (response.status !== 206) throw new Error(`${url} answered ${response.status} for a range`);
    const data = await response.arrayBuffer();
    if (data.byteLength !== length && offset !== 0) throw new Error(`${url} sent ${data.byteLength} of ${length} bytes at ${offset}`);
    return { data };
  },
});
for (const source of Object.values(style.sources)) {
  if ('url' in source && source.url?.startsWith('pmtiles://')) protocol.add(new PMTiles(uncached(source.url.slice('pmtiles://'.length))));
}

const map = new Map({
  container: 'map', style, interactive: false, attributionControl: false, fadeDuration: 0,
  pixelRatio: SCALE, renderWorldCopies: false, minZoom: -2, maxZoom: 22,
  // A block near the top of the world, or a zoomed-out one smaller than the page, shows
  // past the world's edge; MapLibre would move the view to hide that, and the tiles with it.
  transformConstrain: (center, zoom) => ({ center, zoom }),
  canvasContextAttributes: { preserveDrawingBuffer: true, antialias: true },
});
const loaded = new Promise<void>((done) => map.once('load', () => done()));
// MapLibre counts a tile that failed to load as finished, and draws a hole where it was, so
// a block during which anything failed is refused, and drawn again on a fresh page.
let failures: string[] = [];
map.on('error', (event) => {
  const { sourceId, tile } = event as { sourceId?: string; tile?: { tileID?: { canonical?: object } } };
  const where = [sourceId, tile?.tileID?.canonical && JSON.stringify(tile.tileID.canonical)].filter(Boolean).join(' ');
  failures.push(`${event.error?.message ?? event.error}${where ? ` (${where})` : ''}`);
});

/** One drawn tile: its column and row, and the WebP image as base64. */
interface Drawn { x: number; y: number; webp: string }

/**
 * Draws the block of tiles whose first column and row are `x0` and `y0`, at zoom `z` in
 * 256-pixel tiles (MapLibre's zoom, counting 512-pixel tiles, is one lower), and returns the
 * tiles in `wanted`, each a `x,y` key.
 */
async function drawBlock(z: number, x0: number, y0: number, wanted: string[]): Promise<Drawn[]> {
  await loaded;
  const n = Math.min(BLOCK, 2 ** z);
  const world = 2 ** z;
  // The block's middle, as a longitude and latitude.
  const cx = (x0 + n / 2) / world;
  const cy = (y0 + n / 2) / world;
  const lon = cx * 360 - 180;
  const lat = (Math.atan(Math.sinh(Math.PI * (1 - 2 * cy))) * 180) / Math.PI;
  failures = [];
  await new Promise<void>((done) => {
    map.once('idle', () => done());
    map.jumpTo({ center: [lon, lat], zoom: z - 1 });
    map.triggerRepaint();
  });
  if (failures.length) throw new Error(`block ${z}/${x0}/${y0}: ${failures.join('; ')}`);
  const canvas = map.getCanvas();
  const left = ((SIZE - n * TILE) / 2) * SCALE;
  const out = document.createElement('canvas');
  out.width = out.height = TILE * SCALE;
  const context = out.getContext('2d')!;
  const drawn: Drawn[] = [];
  for (const key of wanted) {
    const [x, y] = key.split(',').map(Number);
    context.clearRect(0, 0, out.width, out.height);
    context.drawImage(canvas, left + (x - x0) * TILE * SCALE, left + (y - y0) * TILE * SCALE, TILE * SCALE, TILE * SCALE, 0, 0, TILE * SCALE, TILE * SCALE);
    const blob = await new Promise<Blob>((done, fail) => out.toBlob((b) => (b ? done(b) : fail(new Error('no image'))), 'image/webp', 0.85));
    const bytes = new Uint8Array(await blob.arrayBuffer());
    let binary = '';
    for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
    drawn.push({ x, y, webp: btoa(binary) });
  }
  return drawn;
}

(window as unknown as { drawBlock: typeof drawBlock }).drawBlock = drawBlock;
