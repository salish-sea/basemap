// Refuses an archive that isn't whole, before publish.sh uploads it:
//   node scripts/check_archives.ts build/coast/elevation.pmtiles build/coast/depth.pmtiles ...
// A PMTiles header names where each of its parts (the directories, the metadata and the
// tiles) starts and how long it is, so a whole archive ends where its last part ends. An
// empty file has no header, and a truncated one ends short of its parts. 2026.10.21 was
// published with an empty elevation archive: the machine restarted while elevation_tiles.py
// was writing it, and make took the empty file, newer than its sources, as up to date.

import { closeSync, fstatSync, openSync, readSync } from 'node:fs';

const paths = process.argv.slice(2);
if (paths.length === 0) {
  console.error('usage: node scripts/check_archives.ts ARCHIVE.pmtiles ...');
  process.exit(2);
}

const problem = (path: string): string | undefined => {
  const fd = openSync(path, 'r');
  try {
    const size = fstatSync(fd).size;
    const header = Buffer.alloc(127);
    if (readSync(fd, header, 0, 127, 0) < 127) return `${size} bytes, too short for a header`;
    if (header.toString('latin1', 0, 7) !== 'PMTiles' || header[7] !== 3) return 'no PMTiles v3 header';
    // Offset and length of the root directory, the metadata, the leaf directories and the tiles.
    let end = 0n;
    for (let at = 8; at < 72; at += 16)
      end = [end, header.readBigUInt64LE(at) + header.readBigUInt64LE(at + 8)].reduce((a, b) => (a > b ? a : b));
    if (BigInt(size) !== end) return `${size} bytes, but its header describes ${end}`;
    if (header.readBigUInt64LE(72) === 0n) return 'no tiles';
  } finally {
    closeSync(fd);
  }
};

let failed = false;
for (const path of paths) {
  const why = problem(path);
  if (why) {
    console.error(`${path}: ${why}`);
    failed = true;
  }
}
process.exit(failed ? 1 : 0);
