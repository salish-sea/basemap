// Draws a region's image tiles (decisions/014) from its build, into build/<region>/images/:
//   node scripts/images.ts REGION
// The tiles to draw are listed in build/<region>/images.txt (scripts/image_tiles.py). Each
// block of up to 4 by 4 of them is drawn by viewer/images.html in headless Chromium, which
// returns them as WebP; several pages draw at once. Tiles are written to images.part/ and
// the folder is renamed when every one is there, so a build that stops partway leaves no
// images/ for a publish to trust, and running it again carries on where it stopped. A block
// that fails, because a tile didn't load or it took too long, is drawn again on a freshly
// loaded page, up to TRIES times, and then the run fails.

import { cpus } from 'node:os';
import { existsSync, mkdirSync, readFileSync, renameSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { chromium, type Page } from 'playwright';
import { createServer } from 'vite';

const BLOCK = 4;
const TRIES = 3;
// A block takes a second or two; one that takes this long is stuck.
const BLOCK_TIMEOUT_MS = 120_000;

const region = process.argv[2];
if (!region || !existsSync(`build/${region}/images.txt`)) {
  console.error('usage: node scripts/images.ts REGION, after make has listed build/REGION/images.txt');
  process.exit(2);
}
const out = `build/${region}/images`;
const part = `${out}.part`;

// The blocks to draw, each with the tiles in it that are wanted and not yet drawn.
const blocks = new Map<string, { z: number; x0: number; y0: number; wanted: string[] }>();
let total = 0;
for (const line of readFileSync(`build/${region}/images.txt`, 'utf8').split('\n')) {
  if (!line) continue;
  const [z, x, y] = line.split(' ').map(Number);
  total++;
  const file = `${part}/${z}/${x}/${y}.webp`;
  if (existsSync(file) && statSync(file).size > 0) continue;
  const n = Math.min(BLOCK, 2 ** z);
  const x0 = Math.floor(x / n) * n;
  const y0 = Math.floor(y / n) * n;
  const key = `${z}/${x0}/${y0}`;
  const block = blocks.get(key) ?? { z, x0, y0, wanted: [] };
  block.wanted.push(`${x},${y}`);
  blocks.set(key, block);
}
const queue = [...blocks.values()];
const todo = queue.reduce((sum, b) => sum + b.wanted.length, 0);
console.log(`${total} tiles, ${todo} to draw in ${queue.length} blocks`);

const server = await createServer({ root: 'viewer', configFile: 'viewer/vite.config.ts', server: { port: 5181, strictPort: false }, logLevel: 'warn' });
await server.listen();
const page = `${server.resolvedUrls!.local[0]}images.html?base=/${region}/`;
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const started = Date.now();
let done = 0;
let reported = 0;
try {
  // Each page draws one block at a time; Chromium's software renderer uses several cores
  // for each, so half the machine's is about as many as help.
  const workers = Math.max(1, Math.min(8, Math.floor(cpus().length / 2)));
  type Drawn = { x: number; y: number; webp: string }[];
  const open = async () => {
    const tab = await browser.newPage({ viewport: { width: 1280, height: 1280 } });
    await tab.goto(page);
    await tab.waitForFunction(() => 'drawBlock' in window, null, { timeout: 60_000 });
    return tab;
  };
  const draw = (tab: Page, { z, x0, y0, wanted }: (typeof queue)[number]) => {
    let timer: NodeJS.Timeout | undefined;
    const timeout = new Promise<never>((_, fail) => {
      timer = setTimeout(() => fail(new Error(`block ${z}/${x0}/${y0} took over ${BLOCK_TIMEOUT_MS / 1000} s`)), BLOCK_TIMEOUT_MS);
    });
    const drawing = tab.evaluate(
      ([z, x0, y0, wanted]) => (window as unknown as { drawBlock: (z: number, x0: number, y0: number, w: string[]) => Promise<Drawn> }).drawBlock(z, x0, y0, wanted),
      [z, x0, y0, wanted] as const,
    );
    return Promise.race([drawing, timeout]).finally(() => clearTimeout(timer));
  };
  await Promise.all(Array.from({ length: workers }, async () => {
    let tab = await open();
    for (let block = queue.shift(); block; block = queue.shift()) {
      let drawn: Drawn | undefined;
      for (let attempt = 1; !drawn; attempt++) {
        try {
          drawn = await draw(tab, block);
        } catch (error) {
          if (attempt >= TRIES) throw error;
          console.log(`${(error as Error).message.split('\n')[0]}; drawing it again`);
          // A fresh page forgets the tiles that failed, which MapLibre would not ask for again.
          await tab.close().catch(() => {});
          tab = await open();
        }
      }
      const { z } = block;
      for (const { x, y, webp } of drawn) {
        mkdirSync(`${part}/${z}/${x}`, { recursive: true });
        // Written whole or not at all, so a run that stops mid-write leaves no torn tile to keep.
        writeFileSync(`${part}/${z}/${x}/${y}.webp.tmp`, Buffer.from(webp, 'base64'));
        renameSync(`${part}/${z}/${x}/${y}.webp.tmp`, `${part}/${z}/${x}/${y}.webp`);
      }
      done += drawn.length;
      if (done - reported >= todo / 20 || done === todo) {
        reported = done;
        const seconds = (Date.now() - started) / 1000;
        console.log(`${done} of ${todo} drawn, ${seconds.toFixed(0)} s`);
      }
    }
    await tab.close();
  }));
} finally {
  await browser.close();
  await server.close();
}
rmSync(out, { recursive: true, force: true });
renameSync(part, out);
console.log(`${out}: ${total} tiles`);
