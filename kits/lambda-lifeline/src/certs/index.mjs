// certs: patches function environment to set NODE_EXTRA_CA_CERTS when connecting
// to RDS or Amazon-managed services over TLS. On Node 20+, Lambda no longer
// auto-loads Amazon-specific CA certs.

import { parseArgs, isDryRun, requireFlag, list } from '../util/args.mjs';
import { log, color } from '../util/log.mjs';

const DEFAULT_CA_PATH = '/var/runtime/ca-cert.pem';

export async function certsCommand(argv) {
  const { flags } = parseArgs(argv);
  const apply = !isDryRun(flags);
  const caPath = flags['ca-path'] || DEFAULT_CA_PATH;
  const fnFlag = flags.function;
  const all = flags.all === true;
  const region = flags.region || process.env.AWS_REGION || 'us-east-1';

  log.hdr(`CA cert patcher · ${apply ? color.red('APPLY') : color.yellow('DRY-RUN')}`);
  log.info(`NODE_EXTRA_CA_CERTS will be set to ${color.cyan(caPath)}`);

  if (!fnFlag && !all) {
    log.warn('Neither --function <name> nor --all supplied. Showing planned change only.');
    console.log(`  Set env: ${color.cyan('NODE_EXTRA_CA_CERTS=' + caPath)}`);
    console.log(color.gray('  Run again with --function <name> --apply to execute on AWS.'));
    return;
  }

  let Lambda;
  try {
    Lambda = await import('@aws-sdk/client-lambda');
  } catch {
    throw new Error('AWS SDK not installed. Run `npm install` in the kit directory.');
  }
  const client = new Lambda.LambdaClient({ region });

  const targets = [];
  if (fnFlag) {
    const names = list(fnFlag);
    for (const n of names) targets.push(n);
  } else if (all) {
    // list all functions using nodejs{16,18,20}.x
    let Marker;
    do {
      const resp = await client.send(new Lambda.ListFunctionsCommand({ Marker }));
      for (const fn of resp.Functions || []) {
        if (['nodejs16.x', 'nodejs18.x', 'nodejs20.x', 'nodejs22.x'].includes(fn.Runtime)) {
          targets.push(fn.FunctionName);
        }
      }
      Marker = resp.NextMarker;
    } while (Marker);
    log.info(`--all matched ${targets.length} function(s) in ${region}`);
  }

  if (targets.length === 0) {
    log.warn('No target functions.');
    return;
  }

  for (const name of targets) {
    // 1. Read current config
    const cfg = await client.send(new Lambda.GetFunctionConfigurationCommand({ FunctionName: name }));
    const current = cfg.Environment?.Variables || {};
    if (current.NODE_EXTRA_CA_CERTS === caPath) {
      log.dim(`  ${name} · already set · skip`);
      continue;
    }
    const merged = { ...current, NODE_EXTRA_CA_CERTS: caPath };
    if (!apply) {
      log.info(`[dry-run] would patch ${color.bold(name)} (${Object.keys(current).length} existing env vars)`);
      continue;
    }
    await client.send(new Lambda.UpdateFunctionConfigurationCommand({
      FunctionName: name,
      Environment: { Variables: merged },
    }));
    log.ok(`patched ${name}`);
  }

  log.ok('certs command done.');
}