// Scanner: enumerate Lambda functions across regions, flag Node 16/18/20 runtimes.
// Works in two modes:
//   1) Live AWS: uses @aws-sdk/client-lambda via default credential chain
//   2) Fixture: --fixture <file.json> for demos, CI tests, and air-gapped buyers
//
// All results are normalized to the same schema and written to JSON/CSV/markdown.

import { parseArgs, list } from '../util/args.mjs';
import { log, color } from '../util/log.mjs';
import { writeFileSync, readFileSync } from 'node:fs';

const EOL_RUNTIMES = new Set([
  'nodejs16.x', 'nodejs18.x', 'nodejs20.x',
  'python3.9', 'python3.10',                    // bonus: flagged but not our primary scope
  'ruby3.2',                                    // bonus
  'dotnet6',
  'java8.al2',
  'provided.al2',
]);

const PHASE_DATES = {
  'nodejs16.x': { phase1: '2024-06-12', block_create: '2026-08-31', block_update: '2026-09-30' },
  'nodejs18.x': { phase1: '2025-09-01', block_create: '2026-08-31', block_update: '2026-09-30' },
  'nodejs20.x': { phase1: '2026-04-30', block_create: '2026-08-31', block_update: '2026-09-30' },
  'python3.9':  { phase1: '2025-12-15', block_create: '2026-08-31', block_update: '2026-09-30' },
  'python3.10': { phase1: '2026-10-31', block_create: '2026-11-30', block_update: '2027-01-15' },
  'ruby3.2':    { phase1: '2026-03-31', block_create: '2026-08-31', block_update: '2026-09-30' },
  'dotnet6':    { phase1: '2024-12-20', block_create: '2026-08-31', block_update: '2026-09-30' },
};

const UPGRADE_TARGETS = {
  'nodejs16.x': 'nodejs22.x',
  'nodejs18.x': 'nodejs22.x',
  'nodejs20.x': 'nodejs22.x',
  'python3.9':  'python3.12',
  'python3.10': 'python3.12',
  'ruby3.2':    'ruby3.4',
  'dotnet6':    'dotnet8',
  'java8.al2':  'java21',
  'provided.al2': 'provided.al2023',
};

function daysUntil(isoDate) {
  const target = new Date(isoDate + 'T00:00:00Z').getTime();
  const now = Date.now();
  return Math.floor((target - now) / (1000 * 60 * 60 * 24));
}

function severity(runtime) {
  const dates = PHASE_DATES[runtime];
  if (!dates) return 'unknown';
  const d = daysUntil(dates.block_update);
  if (d <= 0) return 'critical-blocked';
  if (d <= 60) return 'critical';
  if (d <= 180) return 'high';
  return 'medium';
}

async function scanLive({ regions, profile }) {
  let LambdaClient, ListFunctionsCommand, fromIni, STSClient, GetCallerIdentityCommand;
  try {
    ({ LambdaClient, ListFunctionsCommand } = await import('@aws-sdk/client-lambda'));
    ({ STSClient, GetCallerIdentityCommand } = await import('@aws-sdk/client-sts'));
    if (profile) {
      ({ fromIni } = await import('@aws-sdk/credential-providers'));
    }
  } catch {
    throw new Error(
      'AWS SDK not installed. Run `npm install` in the kit dir, or use --fixture <file.json> for offline mode.'
    );
  }

  const creds = profile ? { credentials: fromIni({ profile }) } : {};

  // Discover account id
  let accountId = 'unknown';
  try {
    const sts = new STSClient({ region: regions[0], ...creds });
    const who = await sts.send(new GetCallerIdentityCommand({}));
    accountId = who.Account || 'unknown';
  } catch (e) {
    log.warn(`Could not call STS: ${e.message}. Continuing without account id.`);
  }

  const results = [];
  for (const region of regions) {
    log.dim(`  scanning ${region}…`);
    const client = new LambdaClient({ region, ...creds });
    let Marker;
    do {
      const resp = await client.send(new ListFunctionsCommand({ Marker }));
      for (const fn of resp.Functions || []) {
        results.push(normalizeFunction(fn, accountId, region));
      }
      Marker = resp.NextMarker;
    } while (Marker);
  }
  return results;
}

async function scanFixture(file) {
  const raw = JSON.parse(readFileSync(file, 'utf8'));
  const arr = Array.isArray(raw) ? raw : raw.Functions || [];
  return arr.map(fn =>
    normalizeFunction(fn, fn.AccountId || '000000000000', fn.Region || 'us-east-1')
  );
}

function normalizeFunction(fn, accountId, region) {
  return {
    account_id: accountId,
    region,
    function_name: fn.FunctionName,
    arn: fn.FunctionArn,
    runtime: fn.Runtime,
    handler: fn.Handler,
    memory_mb: fn.MemorySize,
    last_modified: fn.LastModified,
    package_type: fn.PackageType || 'Zip',
    architectures: fn.Architectures || ['x86_64'],
    code_size: fn.CodeSize,
    eol: EOL_RUNTIMES.has(fn.Runtime),
    severity: EOL_RUNTIMES.has(fn.Runtime) ? severity(fn.Runtime) : 'ok',
    recommended_target: UPGRADE_TARGETS[fn.Runtime] || null,
    deprecation_dates: PHASE_DATES[fn.Runtime] || null,
    days_until_block_update: PHASE_DATES[fn.Runtime]
      ? daysUntil(PHASE_DATES[fn.Runtime].block_update)
      : null,
  };
}

function renderTable(rows) {
  if (rows.length === 0) {
    log.ok('No functions using EOL runtimes. You are all green. ✓');
    return;
  }
  const eol = rows.filter(r => r.eol);
  const ok = rows.length - eol.length;
  log.info(`Scanned ${rows.length} functions · ${color.green(ok + ' healthy')} · ${color.red(eol.length + ' at risk')}`);
  if (eol.length === 0) return;

  console.log();
  const widths = { fn: 36, rt: 14, region: 14, sev: 18, days: 6, tgt: 14 };
  const hdr = [
    'Function'.padEnd(widths.fn),
    'Runtime'.padEnd(widths.rt),
    'Region'.padEnd(widths.region),
    'Severity'.padEnd(widths.sev),
    'Days'.padEnd(widths.days),
    'Target',
  ].join(' ');
  console.log(color.bold(hdr));
  console.log(color.gray('-'.repeat(hdr.length)));
  for (const r of eol) {
    const sevColor = r.severity.startsWith('critical') ? color.red : color.yellow;
    console.log([
      r.function_name.slice(0, widths.fn - 1).padEnd(widths.fn),
      r.runtime.padEnd(widths.rt),
      r.region.padEnd(widths.region),
      sevColor(r.severity.padEnd(widths.sev)),
      String(r.days_until_block_update ?? '?').padEnd(widths.days),
      r.recommended_target || '-',
    ].join(' '));
  }
  console.log();
  log.warn('Next: run `lambda-lifeline codemod --path <your-repo>` then `audit`, `iac`, and `deploy`.');
}

function toCSV(rows) {
  const cols = [
    'account_id','region','function_name','runtime','severity',
    'days_until_block_update','recommended_target','arn',
  ];
  const esc = v => {
    if (v == null) return '';
    const s = String(v);
    return /[,"\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [cols.join(',')]
    .concat(rows.map(r => cols.map(c => esc(r[c])).join(',')))
    .join('\n');
}

function toMarkdown(rows) {
  const eol = rows.filter(r => r.eol);
  const lines = [
    '# Lambda Lifeline — scan report',
    '',
    `**Scanned:** ${new Date().toISOString()}  `,
    `**Total functions:** ${rows.length}  `,
    `**At-risk functions:** ${eol.length}`,
    '',
  ];
  if (eol.length === 0) {
    lines.push('✅ No functions using EOL runtimes.');
    return lines.join('\n');
  }
  lines.push('| Function | Runtime | Region | Severity | Days → block_update | Target |');
  lines.push('|---|---|---|---|---|---|');
  for (const r of eol) {
    lines.push(`| \`${r.function_name}\` | ${r.runtime} | ${r.region} | ${r.severity} | ${r.days_until_block_update ?? '?'} | ${r.recommended_target ?? '-'} |`);
  }
  lines.push('', '## Primary source', 'https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html');
  return lines.join('\n');
}

export async function scanCommand(argv) {
  const { flags } = parseArgs(argv);
  const regions = list(flags.regions).length
    ? list(flags.regions)
    : [process.env.AWS_REGION || 'us-east-1'];
  const profile = flags.profile || process.env.AWS_PROFILE;
  const outPath = flags.out;
  const format = flags.format || (outPath ? outPath.split('.').pop() : 'table');
  const fixture = flags.fixture;

  const machineOut = flags.json || format === 'json' || format === 'csv' || format === 'md' || format === 'markdown';
  if (!machineOut) {
    log.hdr(fixture ? `Scanning fixture: ${fixture}` : `Scanning ${regions.length} region(s)`);
  } else {
    console.error(`[lambda-lifeline] ${fixture ? 'fixture=' + fixture : 'regions=' + regions.join(',')}`);
  }

  const rows = fixture ? await scanFixture(fixture) : await scanLive({ regions, profile });

  if (flags.json || format === 'json') {
    const out = JSON.stringify(rows, null, 2);
    if (outPath) { writeFileSync(outPath, out); log.ok(`Wrote ${outPath} (${rows.length} rows)`); }
    else console.log(out);
  } else if (format === 'csv') {
    const out = toCSV(rows);
    if (outPath) { writeFileSync(outPath, out); log.ok(`Wrote ${outPath}`); }
    else console.log(out);
  } else if (format === 'md' || format === 'markdown') {
    const out = toMarkdown(rows);
    if (outPath) { writeFileSync(outPath, out); log.ok(`Wrote ${outPath}`); }
    else console.log(out);
  } else {
    renderTable(rows);
    if (outPath) { writeFileSync(outPath, JSON.stringify(rows, null, 2)); log.ok(`Wrote ${outPath}`); }
  }

  const atRisk = rows.filter(r => r.eol).length;
  if (flags.strict && atRisk > 0) process.exit(1);
}