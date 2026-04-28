import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdirSync, writeFileSync, readFileSync, mkdtempSync, rmSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const CLI = join(__dirname, '..', 'bin', 'cli.mjs');

function run(args) {
  return spawnSync('node', [CLI, ...args], { encoding: 'utf8' });
}

function scratch() {
  const dir = mkdtempSync(join(tmpdir(), 'll-codemod-'));
  return { dir, cleanup: () => rmSync(dir, { recursive: true, force: true }) };
}

test('codemod dry-run finds assert imports but does not write', () => {
  const { dir, cleanup } = scratch();
  try {
    const srcFile = join(dir, 'foo.mjs');
    const original = `import c from './c.json' with { type: 'json' };\nconsole.log(c);\n`;
    writeFileSync(srcFile, original);
    const r = run(['codemod', '--path', dir]);
    assert.equal(r.status, 0, r.stderr);
    assert.match(r.stdout, /assert-to-with/);
    assert.match(r.stdout, /DRY-RUN/);
    assert.equal(readFileSync(srcFile, 'utf8'), original, 'file must be untouched in dry-run');
  } finally { cleanup(); }
});

test('codemod --apply rewrites assert to with', () => {
  const { dir, cleanup } = scratch();
  try {
    const srcFile = join(dir, 'foo.mjs');
    writeFileSync(srcFile, `import c from './c.json' with { type: 'json' };\n`);
    const r = run(['codemod', '--path', dir, '--apply']);
    assert.equal(r.status, 0, r.stderr);
    const result = readFileSync(srcFile, 'utf8');
    assert.match(result, /with \{ type: 'json' \}/);
    assert.doesNotMatch(result, /assert \{/);
  } finally { cleanup(); }
});

test('codemod --apply rewrites dynamic import assert', () => {
  const { dir, cleanup } = scratch();
  try {
    const srcFile = join(dir, 'dyn.mjs');
    writeFileSync(srcFile, `const m = await import('./f.json', { with: { type: 'json' } });\n`);
    const r = run(['codemod', '--path', dir, '--apply']);
    assert.equal(r.status, 0, r.stderr);
    const result = readFileSync(srcFile, 'utf8');
    assert.match(result, /with:/);
    assert.doesNotMatch(result, /assert:/);
  } finally { cleanup(); }
});

test('codemod flags Buffer negative-index lint', () => {
  const { dir, cleanup } = scratch();
  try {
    const srcFile = join(dir, 'buf.js');
    writeFileSync(srcFile, `buf.toString('utf8', 0, -1);\n`);
    const r = run(['codemod', '--path', dir]);
    assert.equal(r.status, 0);
    assert.match(r.stdout, /buffer-negative-index/);
    assert.match(r.stdout, /lint/);
  } finally { cleanup(); }
});

test('codemod on clean code reports zero hits', () => {
  const { dir, cleanup } = scratch();
  try {
    writeFileSync(join(dir, 'clean.mjs'), `import c from './c.json' with { type: 'json' };\n`);
    const r = run(['codemod', '--path', dir]);
    assert.equal(r.status, 0);
    assert.match(r.stdout, /No codemod hits/);
  } finally { cleanup(); }
});