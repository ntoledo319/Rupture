import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const CLI = join(__dirname, '..', 'bin', 'cli.mjs');

function run(args) {
  return spawnSync('node', [CLI, ...args], { encoding: 'utf8' });
}
function scratch() {
  const dir = mkdtempSync(join(tmpdir(), 'll-audit-'));
  return { dir, cleanup: () => rmSync(dir, { recursive: true, force: true }) };
}

test('audit detects outdated sharp and flags node-sass as dead', () => {
  const { dir, cleanup } = scratch();
  try {
    writeFileSync(join(dir, 'package.json'), JSON.stringify({
      name: 'x', version: '1.0.0',
      dependencies: { sharp: '^0.32.6' },
      devDependencies: { 'node-sass': '^7.0.0' },
    }));
    const r = run(['audit', '--path', dir]);
    assert.equal(r.status, 0);
    assert.match(r.stdout, /sharp/);
    assert.match(r.stdout, /UPGRADE/);
    assert.match(r.stdout, /node-sass/);
    assert.match(r.stdout, /DEAD/);
  } finally { cleanup(); }
});

test('audit --strict exits 1 when risks found', () => {
  const { dir, cleanup } = scratch();
  try {
    writeFileSync(join(dir, 'package.json'), JSON.stringify({
      name: 'x', version: '1.0.0', dependencies: { 'fibers': '^5.0.0' },
    }));
    const r = run(['audit', '--path', dir, '--strict']);
    assert.equal(r.status, 1);
  } finally { cleanup(); }
});

test('audit passes on clean deps', () => {
  const { dir, cleanup } = scratch();
  try {
    writeFileSync(join(dir, 'package.json'), JSON.stringify({
      name: 'x', version: '1.0.0',
      dependencies: { 'sharp': '^0.33.2', 'bcrypt': '^5.1.1' },
    }));
    const r = run(['audit', '--path', dir, '--strict']);
    assert.equal(r.status, 0);
    assert.match(r.stdout, /All native deps are Node 22-compatible/);
  } finally { cleanup(); }
});

test('audit --json emits findings array', () => {
  const { dir, cleanup } = scratch();
  try {
    writeFileSync(join(dir, 'package.json'), JSON.stringify({
      name: 'x', version: '1.0.0', dependencies: { sharp: '^0.32.0' },
    }));
    const r = run(['audit', '--path', dir, '--json']);
    assert.equal(r.status, 0);
    const data = JSON.parse(r.stdout);
    assert.ok(Array.isArray(data.findings));
    assert.equal(data.findings[0].name, 'sharp');
    assert.equal(data.findings[0].status, 'upgrade-required');
  } finally { cleanup(); }
});