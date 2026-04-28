import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const CLI = join(__dirname, '..', 'bin', 'cli.mjs');

function run(args) {
  return spawnSync('node', [CLI, ...args], { encoding: 'utf8' });
}

test('plan --function prints a numbered deployment plan', () => {
  const r = run(['plan', '--function', 'my-fn']);
  assert.equal(r.status, 0, r.stderr);
  assert.match(r.stdout, /Deploy plan for my-fn/);
  assert.match(r.stdout, /Snapshot current live version/);
  assert.match(r.stdout, /Publish new version/);
  assert.match(r.stdout, /weighted routing/);
  assert.match(r.stdout, /rollback/i);
});

test('plan honors custom stages', () => {
  const r = run(['plan', '--function', 'x', '--stages', '10,50,100', '--wait-minutes', '5']);
  assert.equal(r.status, 0, r.stderr);
  assert.match(r.stdout, /Shift 10%/);
  assert.match(r.stdout, /Shift 50%/);
  assert.match(r.stdout, /hold 5 min/);
});

test('deploy without --apply stays in dry-run (no AWS calls)', () => {
  const r = run(['deploy', '--function', 'my-fn']);
  assert.equal(r.status, 0, r.stderr);
  assert.match(r.stdout, /DRY-RUN/);
});

test('deploy --apply without --alarm throws', () => {
  const r = run(['deploy', '--function', 'x', '--apply']);
  assert.notEqual(r.status, 0);
  assert.match(r.stderr + r.stdout, /--alarm/);
});