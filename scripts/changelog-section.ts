// Prints a version's section of CHANGELOG.md, for its GitHub release (scripts/release.sh):
//   node scripts/changelog-section.ts 2026.11.4 2026.11.3 2026-11-25
// When the changelog has no section for the version yet, its Unreleased section becomes
// the version's, headed with its date and linking its index page and the changes since
// PREVIOUS, and CHANGELOG.md is rewritten, to be committed with the README. It fails when
// there is neither, so a version can't be announced without saying what changed.

import { readFileSync, writeFileSync } from 'node:fs';

const [version, previous, date] = process.argv.slice(2);
if (!version || !date) {
  console.error('usage: node scripts/changelog-section.ts VERSION PREVIOUS|"" YYYY-MM-DD');
  process.exit(2);
}
const path = 'CHANGELOG.md';
let text = readFileSync(path, 'utf8');

/** The body of the section headed `## <title>`, up to the next section, or undefined. */
const section = (title: string) => {
  const start = text.split('\n').findIndex((line) => line === `## ${title}` || line.startsWith(`## ${title} `));
  if (start < 0) return undefined;
  const lines = text.split('\n');
  const end = lines.findIndex((line, i) => i > start && line.startsWith('## '));
  return { start, end: end < 0 ? lines.length : end, body: lines.slice(start + 1, end < 0 ? undefined : end).join('\n').trim() };
};

let found = section(version);
if (!found) {
  const unreleased = section('Unreleased');
  if (!unreleased?.body) {
    console.error(`${path} has no section for ${version} and nothing under "## Unreleased"`);
    process.exit(1);
  }
  const links = [`[Index page](https://tiles.salishsea.io/${version}/index.html)`];
  if (previous) links.push(`[Changes](https://github.com/salish-sea/basemap/compare/${previous}...${version})`);
  const lines = text.split('\n');
  lines.splice(unreleased.start, unreleased.end - unreleased.start,
    '## Unreleased', '', `## ${version} — ${date}`, '', links.join(' · '), '', unreleased.body, '');
  text = lines.join('\n');
  writeFileSync(path, text);
  found = section(version)!;
}
process.stdout.write(found.body + '\n');
