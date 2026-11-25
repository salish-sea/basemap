// Prints what changed in a version, from CHANGELOG.md, for its GitHub release (scripts/release.sh):
//   node scripts/changelog-section.ts 2026.11.4 2026.11.3 2026-11-25
// A change says what it does under "## Unreleased" when it is made, so the changelog as it
// stood at the version's tag holds exactly that version's changes, whatever has been merged
// since. Those entries are what is printed, and, when the checkout's CHANGELOG.md has no
// section for the version yet, they are moved there from its Unreleased section into one
// headed with DATE that links the version's index page and the changes since PREVIOUS, to be
// committed with the README. Links to files in the repository are printed as links to them at
// the tag, since a release's notes can't follow a relative link. It fails when the tag's
// changelog says nothing about the version, so a version can't be announced without that.

import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';

const [version, previous, date] = process.argv.slice(2);
if (!version || !date) {
  console.error('usage: node scripts/changelog-section.ts VERSION PREVIOUS|"" YYYY-MM-DD');
  process.exit(2);
}
const path = 'CHANGELOG.md';
const repo = 'https://github.com/salish-sea/basemap';

/** The section headed `## <title>` in `text`: its lines' span and its body, or undefined. */
function section(text: string, title: string) {
  const lines = text.split('\n');
  const start = lines.findIndex((line) => line === `## ${title}` || line.startsWith(`## ${title} `));
  if (start < 0) return undefined;
  const next = lines.findIndex((line, i) => i > start && line.startsWith('## '));
  const end = next < 0 ? lines.length : next;
  return { start, end, body: lines.slice(start + 1, end).join('\n').trim() };
}

let tagged: string;
try {
  tagged = execFileSync('git', ['show', `${version}:${path}`], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
} catch {
  console.error(`${version} has no ${path}; is it tagged, and was the changelog there yet?`);
  process.exit(1);
}
// The version's own section, if the tag already has one; otherwise what was unreleased then.
const changes = (section(tagged, version) ?? section(tagged, 'Unreleased'))?.body
  // The heading's links, which a version's own section starts with, are the release's own.
  .replace(/^\[Index page\].*\n+/, '');
if (!changes) {
  console.error(`${path} at ${version} has no section for it and nothing under "## Unreleased"`);
  process.exit(1);
}

const text = readFileSync(path, 'utf8');
if (!section(text, version)) {
  const unreleased = section(text, 'Unreleased');
  if (!unreleased) {
    console.error(`${path} has no "## Unreleased" section to move ${version}'s changes out of`);
    process.exit(1);
  }
  const lines = text.split('\n');
  // What has been added to Unreleased since the tag stays there.
  const moved = new Set(changes.split('\n').filter((line) => line.trim()));
  const kept = lines.slice(unreleased.start + 1, unreleased.end).filter((line) => line.trim() && !moved.has(line));
  const links = [`[Index page](https://tiles.salishsea.io/${version}/index.html)`];
  if (previous) links.push(`[Changes](${repo}/compare/${previous}...${version})`);
  lines.splice(unreleased.start, unreleased.end - unreleased.start,
    '## Unreleased', '', ...(kept.length ? [...kept, ''] : []), `## ${version} — ${date}`, '', links.join(' · '), '', changes, '');
  writeFileSync(path, lines.join('\n'));
  // An entry reworded since the tag stays behind, and would be announced again with the next
  // version, so whatever stays is shown for the releaser to check.
  if (kept.length) console.error(`left under Unreleased in ${path}; check none is a released entry reworded since the tag:\n${kept.join('\n')}`);
}
// A link to a file in the repository, such as decisions/014-….md, as a link to it at the tag,
// and an image in it as the image itself.
process.stdout.write(changes
  .replace(/!\[([^\]]*)\]\((?![a-z]+:|#)([^)]+)\)/g, `![$1](https://raw.githubusercontent.com/salish-sea/basemap/${version}/$2)`)
  .replace(/(?<!!)\[([^\]]*)\]\((?![a-z]+:|#)([^)]+)\)/g, `[$1](${repo}/blob/${version}/$2)`) + '\n');
