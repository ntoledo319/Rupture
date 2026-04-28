import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { join, dirname } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const CLI = join(__dirname, '..', 'bin', 'cli.mjs');
const FIXTURE = join(__dirname, 'fixtures', 'lambda-inventory.json');

function run(args) {
  return spawnSync('node', [CLI, ...args], { encoding: 'utf8' });
}

test('scan --fixture prints a summary with at-risk counts', () => {
  const r = run(['scan', '--fixture', FIXTURE]);
  assert.equal(r.status, 0, r.stderr || r.stdout);
  assert.match(r.stdout, /Scanned 6 functions/);
  assert.match(r.stdout, /5 at risk/);   // 3 Node EOL + python 3.10 + ruby 3.2
  assert.match(r.stdout, /nodejs20\.x/);
  assert.match(r.stdout, /nodejs18\.x/);
  assert.match(r.stdout, /nodejs16\.x/);
});

test('scan --fixture --json emits well-formed JSON', () => {
  const r = run(['scan', '--fixture', FIXTURE, '--json']);
  assert.equal(r.status, 0, r.stderr);
  const data = JSON.parse(r.stdout);
  assert.equal(data.length, 6);
  const eol = data.filter(d => d.eol);
  assert.equal(eol.length, 5);
  const orders = data.find(d => d.function_name === 'api-orders-ingest');
  assert.equal(orders.runtime, 'nodejs20.x');
  assert.equal(orders.recommended_target, 'nodejs22.x');
  assert.ok(orders.days_until_block_update > 100); // Sep 30 2026 > 100 days from scan date
});

test('scan --fixture --format csv emits CSV header', () => {
  const r = run(['scan', '--fixture', FIXTURE, '--format', 'csv']);
  assert.equal(r.status, 0, r.stderr);
  assert.match(r.stdout, /^account_id,region,function_name,runtime,severity/m);
});

test('scan --fixture --format md emits a markdown table', () => {
  const r = run(['scan', '--fixture', FIXTURE, '--format', 'md']);
  assert.equal(r.status, 0, r.stderr);
  assert.match(r.stdout, /# Lambda Lifeline — scan report/);
  assert.match(r.stdout, /\| Function \| Runtime/);
});

test('scan --strict exits 1 when at-risk functions exist', () => {
  const r = run(['scan', '--fixture', FIXTURE, '--strict']);
  assert.equal(r.status, 1);
});

test('help output contains all commands', () => {
  const r = run(['help']);
  assert.equal(r.status, 0);
  for (const cmd of ['scan', 'codemod', 'audit', 'certs', 'iac', 'plan', 'deploy', 'rollback']) {
    assert.match(r.stdout, new RegExp(`\\b${cmd}\\b`));
  }
});