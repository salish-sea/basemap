// Draws the landmarks' icons (style/icons/, from Maki) into a sprite of their own, which the
// style names beside Protomaps' (decisions/015):
//   node scripts/sprite.ts build/sprites/landmarks
// writes landmarks.png and landmarks.json, and @2x versions for high-density screens. Each
// icon is Maki's 15-pixel drawing in slate, with a white edge so it reads over land, water
// and relief alike, in a cell PAD pixels wider on every side. Chromium draws them, as it
// draws the image tiles, so the build needs nothing more.

import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname } from 'node:path';
import { chromium } from 'playwright';

const ICONS = { lighthouse: 'lighthouse', tower: 'communications-tower', landmark: 'landmark' } as const;
const SIZE = 15;
const PAD = 2;
const INK = '#3f4f63';

const out = process.argv[2];
if (!out) {
  console.error('usage: node scripts/sprite.ts OUT, as build/sprites/landmarks');
  process.exit(2);
}
mkdirSync(dirname(out), { recursive: true });

// Each icon's drawing, inked, with a white stroke under it for its edge.
const svgs = Object.entries(ICONS).map(([name, file]) => {
  const svg = readFileSync(`style/icons/${file}.svg`, 'utf8')
    .replace(/<path /g, `<path fill="${INK}" stroke="#fff" stroke-width="2" stroke-linejoin="round" paint-order="stroke" `)
    .replace(/viewBox="0 0 15 15"/, `viewBox="${-PAD} ${-PAD} ${SIZE + 2 * PAD} ${SIZE + 2 * PAD}"`)
    .replace(/width="15" height="15"/, `width="${SIZE + 2 * PAD}" height="${SIZE + 2 * PAD}"`);
  return { name, svg };
});

const browser = await chromium.launch({ env: { ...process.env, LD_PRELOAD: '' } });
try {
  const page = await browser.newPage();
  for (const ratio of [1, 2]) {
    const cell = (SIZE + 2 * PAD) * ratio;
    const png: string = await page.evaluate(async ({ svgs, cell }) => {
      const canvas = document.createElement('canvas');
      canvas.width = cell * svgs.length;
      canvas.height = cell;
      const context = canvas.getContext('2d')!;
      for (const [i, { svg }] of svgs.entries()) {
        const image = new Image();
        image.src = `data:image/svg+xml;base64,${btoa(svg)}`;
        await image.decode();
        context.drawImage(image, i * cell, 0, cell, cell);
      }
      return canvas.toDataURL('image/png').split(',')[1]!;
    }, { svgs, cell });
    const suffix = ratio === 1 ? '' : `@${ratio}x`;
    writeFileSync(`${out}${suffix}.png`, Buffer.from(png, 'base64'));
    const index = Object.fromEntries(svgs.map(({ name }, i) => [name, { x: i * cell, y: 0, width: cell, height: cell, pixelRatio: ratio }]));
    writeFileSync(`${out}${suffix}.json`, JSON.stringify(index, null, 1) + '\n');
  }
} finally {
  await browser.close();
}
console.log(`${out}: ${svgs.map((s) => s.name).join(', ')}`);
