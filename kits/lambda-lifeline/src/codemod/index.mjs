// Codemod: rewrite Node.js 20 code for Node.js 22 compatibility.
// Rules:
//   assert-to-with   : `import x from './f' with { type: 'json' }` → `with`
//   buffer-safety    : flag Buffer.toString() calls with negative indices (lint, not rewrite)
//   streams-hwm      : flag streams constructed without explicit highWaterMark (lint)
//   require-assert   : CJS equivalent `require('x', { assert: {...} })` callouts
//
// Default is DRY RUN. Pass --apply to rewrite files in place. All edits are minimal,
// whitespace-preserving, and reversible via version control.

import { parseArgs, list, isDryRun, boolFlag } from '../util/args.mjs';
import { log, color } from '../util/log.mjs';
import { readFileSync, writeFileSync, statSync } from 'node:fs';
import { readdir } from 'node:fs/promises';
import { join, extname, relative } from 'node:path';

const DEFAULT_EXT = ['.js', '.mjs', '.cjs', '.ts', '.tsx', '.jsx'];
const IGNORE_DIRS = new Set(['node_modules', '.git', 'dist', 'build', '.next', '.turbo', 'coverage', '.aws-sam', 'cdk.out']);

export const RULES = {
  'assert-to-with': {
    description: 'Rewrite ESM `import ... assert { type: "json" }` to `import ... with { type: "json" }`',
    // Matches:
    //   import x from './f.json' with { type: 'json' };
    //   import x from './f.json' with {type:"json"};
    //   } from './f.json' with { type: 'json' }
    pattern: /(\bfrom\s+['"][^'"]+['"]\s+)assert(\s*\{[^}]*\})/g,
    replace: (_m, pre, obj) => `${pre}with${obj}`,
    kind: 'rewrite',
  },
  'dynamic-import-assert': {
    description: 'Rewrite dynamic `import(x, { with: { type: "json" } })` → `{ with: { type: "json" } }`',
    pattern: /import\(([^,)]+),\s*\{\s*assert\s*:/g,
    replace: (_m, spec) => `import(${spec}, { with:`,
    kind: 'rewrite',
  },
  'buffer-negative-index': {
    description: 'Flag Buffer.toString(enc, start, end) with negative end (throws in Node 22)',
    // Heuristic lint — matches .toString('utf8', -1) style calls
    pattern: /\.toString\s*\(\s*['"][^'"]+['"]\s*,\s*-?\d+\s*,\s*-\d+\s*\)/g,
    kind: 'lint',
    message: 'Negative end index to Buffer.toString throws RangeError in Node 22. Convert to a non-negative length.',
  },
  'streams-hwm': {
    description: 'Flag stream constructors without explicit highWaterMark (default changed 16KB→64KB)',
    pattern: /new\s+(Readable|Writable|Transform|Duplex)\s*\(\s*\{[^}]*\}\s*\)/g,
    kind: 'lint',
    message: 'Node 22 changed default highWaterMark to 64KB. Set an explicit value if memory-constrained.',
    guard: (match) => !/highWaterMark/.test(match),
  },
};

async function walk(dir, exts) {
  const out = [];
  const entries = await readdir(dir, { withFileTypes: true });
  for (const entry of entries) {
    if (entry.name.startsWith('.') && entry.name !== '.') {
      // allow dotfiles at root only
    }
    if (IGNORE_DIRS.has(entry.name)) continue;
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...(await walk(full, exts)));
    } else if (entry.isFile() && exts.includes(extname(entry.name))) {
      out.push(full);
    }
  }
  return out;
}

function applyRule(name, rule, source) {
  const edits = [];
  if (rule.kind === 'rewrite') {
    let changed = source;
    changed = changed.replace(rule.pattern, (...args) => {
      const match = args[0];
      edits.push({ rule: name, match });
      return rule.replace(...args);
    });
    return { changed, edits };
  } else {
    // lint: report, no rewrite
    const matches = [...source.matchAll(rule.pattern)];
    for (const m of matches) {
      if (rule.guard && !rule.guard(m[0])) continue;
      const before = source.slice(0, m.index);
      const line = before.split('\n').length;
      edits.push({ rule: name, line, match: m[0].slice(0, 80) });
    }
    return { changed: source, edits };
  }
}

export async function codemodCommand(argv) {
  const { flags } = parseArgs(argv);
  const path = flags.path || '.';
  const apply = !isDryRun(flags);
  const extArg = list(flags.ext);
  const exts = extArg.length ? extArg : DEFAULT_EXT;
  const enabledRules = list(flags.rules);
  const rules = enabledRules.length
    ? Object.fromEntries(Object.entries(RULES).filter(([k]) => enabledRules.includes(k)))
    : RULES;

  log.hdr(`Codemod: ${apply ? color.red('APPLY') : color.yellow('DRY-RUN')} · ${path}`);
  if (!apply) log.warn('No files will be written. Pass --apply to execute.');

  const files = statSync(path).isDirectory() ? await walk(path, exts) : [path];
  log.dim(`  ${files.length} source file(s) found`);

  let filesChanged = 0;
  let totalEdits = 0;
  const lintFindings = [];

  for (const file of files) {
    const src = readFileSync(file, 'utf8');
    let current = src;
    const fileEdits = [];
    for (const [name, rule] of Object.entries(rules)) {
      const { changed, edits } = applyRule(name, rule, current);
      if (rule.kind === 'rewrite' && changed !== current) {
        current = changed;
      }
      if (edits.length) {
        fileEdits.push({ rule: name, edits });
        if (rule.kind === 'lint') {
          for (const e of edits) {
            lintFindings.push({ file: relative(process.cwd(), file), ...e, message: rule.message });
          }
        }
      }
    }

    if (fileEdits.length) {
      filesChanged++;
      totalEdits += fileEdits.reduce((a, b) => a + b.edits.length, 0);
      const rel = relative(process.cwd(), file);
      for (const fe of fileEdits) {
        const isLint = RULES[fe.rule].kind === 'lint';
        const tag = isLint ? color.yellow('[lint]') : color.green('[rewrite]');
        log.info(`${tag} ${rel} · ${fe.rule} · ${fe.edits.length} hit(s)`);
      }
      if (apply && current !== src) {
        writeFileSync(file, current);
      }
    }
  }

  console.log();
  if (filesChanged === 0) {
    log.ok('No codemod hits. Your code looks Node 22-ready on the matched rules.');
  } else {
    log.ok(`${filesChanged} file(s) with ${totalEdits} edit(s). ${apply ? 'Applied.' : 'Preview only.'}`);
  }
  if (lintFindings.length) {
    log.warn(`${lintFindings.length} lint finding(s) need human review (cannot auto-fix safely).`);
    if (boolFlag(flags, 'json')) log.json(lintFindings);
  }
  if (flags.strict && (lintFindings.length > 0 || filesChanged > 0) && !apply) process.exit(1);
}