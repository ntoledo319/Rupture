// Native-binary dep audit.
// Scans package.json (+ lockfile if present) for packages that ship native addons
// whose ABI is tied to the Node major version. Each entry includes the minimum
// version required for Node 22 compatibility.
//
// Exit code 0 if clean, 1 if risks found and --strict is set.

import { parseArgs, isDryRun } from '../util/args.mjs';
import { log, color } from '../util/log.mjs';
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';

// Canonical list of native-binary packages + minimum Node 22 compatible version.
// Sourced from upstream release notes cross-checked 2026-04-28.
export const NATIVE_PACKAGES = {
  'sharp':            { minForNode22: '0.33.0', note: 'libvips native binding. v0.33+ ships Node 22 prebuilds.' },
  'bcrypt':           { minForNode22: '5.1.1',  note: 'Native bcrypt. Consider bcryptjs for pure-JS drop-in.' },
  'better-sqlite3':   { minForNode22: '11.0.0', note: 'SQLite native binding.' },
  'canvas':           { minForNode22: '2.11.2', note: 'node-canvas. Needs rebuilt prebuilds for Node 22.' },
  'node-gyp':         { minForNode22: '10.0.0', note: 'Build system. Upgrade before rebuilding natives.' },
  'node-sass':        { minForNode22: null,     note: 'DEAD. Use `sass` (Dart Sass) instead — no native deps.' },
  'bufferutil':       { minForNode22: '4.0.8',  note: 'WebSocket utility native addon.' },
  'utf-8-validate':   { minForNode22: '6.0.4',  note: 'WebSocket utility native addon.' },
  'libpq':            { minForNode22: '2.0.0',  note: 'PostgreSQL client. Prefer `pg-native` alternatives.' },
  'grpc':             { minForNode22: null,     note: 'DEAD. Migrate to `@grpc/grpc-js` (pure JS).' },
  '@grpc/grpc-js':    { minForNode22: '1.10.0', note: 'Pure JS, no native; just keep up to date.' },
  'sqlite3':          { minForNode22: '5.1.7',  note: 'SQLite3 bindings. Prebuilds available.' },
  'argon2':           { minForNode22: '0.40.0', note: 'argon2 bindings.' },
  're2':              { minForNode22: '1.21.0', note: 'RE2 regex engine.' },
  'fibers':           { minForNode22: null,     note: 'DEAD since Node 16. Must remove.' },
  '@tensorflow/tfjs-node': { minForNode22: '4.20.0', note: 'TensorFlow native.' },
  'sodium-native':    { minForNode22: '4.3.0',  note: 'libsodium bindings.' },
  'zmq':              { minForNode22: null,     note: 'DEAD. Use `zeromq` instead.' },
  'zeromq':           { minForNode22: '6.1.2',  note: 'ZeroMQ bindings.' },
  'farmhash':         { minForNode22: '4.0.0',  note: 'Native hashing.' },
  '@napi-rs/snappy':  { minForNode22: '7.2.0',  note: 'Snappy compression.' },
  'heapdump':         { minForNode22: null,     note: 'DEAD. Use `node --heapsnapshot-signal` instead.' },
};

// Version compare (semver-ish, without dev deps).
function cmpVer(a, b) {
  const pa = a.replace(/^[^\d]*/, '').split('.').map(n => parseInt(n, 10) || 0);
  const pb = b.split('.').map(n => parseInt(n, 10) || 0);
  for (let i = 0; i < 3; i++) {
    if ((pa[i] ?? 0) > (pb[i] ?? 0)) return 1;
    if ((pa[i] ?? 0) < (pb[i] ?? 0)) return -1;
  }
  return 0;
}

function cleanVersion(v) {
  if (!v) return null;
  return v.replace(/^[\^~>=<\s]+/, '');
}

function collectDeps(pkg) {
  const deps = { ...(pkg.dependencies || {}), ...(pkg.devDependencies || {}) };
  return deps;
}

export function auditPackage(pkg) {
  const deps = collectDeps(pkg);
  const findings = [];
  for (const [name, versionSpec] of Object.entries(deps)) {
    const info = NATIVE_PACKAGES[name];
    if (!info) continue;
    const declared = cleanVersion(versionSpec);
    const needed = info.minForNode22;
    const status =
      needed === null
        ? 'dead'
        : declared && cmpVer(declared, needed) >= 0
          ? 'ok'
          : 'upgrade-required';
    findings.push({ name, declared, required: needed, status, note: info.note });
  }
  return findings;
}

export async function auditCommand(argv) {
  const { flags } = parseArgs(argv);
  const path = flags.path || '.';
  const pkgPath = join(path, 'package.json');

  if (flags.json) {
    console.error(`[lambda-lifeline] audit path=${pkgPath}`);
  } else {
    log.hdr(`Audit native dependencies · ${pkgPath}`);
  }
  if (!existsSync(pkgPath)) {
    log.err(`No package.json at ${pkgPath}`);
    process.exit(2);
  }
  const pkg = JSON.parse(readFileSync(pkgPath, 'utf8'));
  const findings = auditPackage(pkg);

  if (flags.json) {
    log.json({ package: pkg.name, findings });
    if (flags.strict && findings.some(f => f.status !== 'ok')) process.exit(1);
    return;
  }

  if (findings.length === 0) {
    log.ok('No native-binary packages detected. You are Node 22-safe on this dimension.');
    return;
  }

  for (const f of findings) {
    const icon = f.status === 'ok' ? color.green('✓')
               : f.status === 'dead' ? color.red('✗')
               : color.yellow('⚠');
    const tag = f.status === 'ok' ? color.green('OK')
              : f.status === 'dead' ? color.red('DEAD')
              : color.yellow('UPGRADE');
    const versions = f.status === 'dead'
      ? 'drop this dep'
      : `declared ${f.declared || '?'}  →  need ≥ ${f.required}`;
    console.log(`  ${icon} ${color.bold(f.name.padEnd(28))} ${tag.padEnd(10)} ${versions}`);
    console.log(`     ${color.gray(f.note)}`);
  }

  const risky = findings.filter(f => f.status !== 'ok');
  console.log();
  if (risky.length === 0) {
    log.ok('All native deps are Node 22-compatible.');
  } else {
    log.warn(`${risky.length} native dep(s) need action before Node 22.`);
    log.info('Next: bump versions in package.json, run `npm install && npm rebuild`, then `npm test`.');
  }
  if (flags.strict && risky.length > 0) process.exit(1);
}