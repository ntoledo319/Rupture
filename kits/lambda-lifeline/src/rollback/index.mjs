// Roll a function alias back to its previous version.
// Finds previous version by querying alias history (alias config stores AliasArn, which has version).
// Simple strategy: if alias currently points at version N, roll back to N-1 (skipping $LATEST).

import { parseArgs, isDryRun, requireFlag } from '../util/args.mjs';
import { log, color } from '../util/log.mjs';

export async function rollbackCommand(argv) {
  const { flags } = parseArgs(argv);
  const apply = !isDryRun(flags);
  const fn = requireFlag(flags, 'function');
  const aliasName = flags.alias || 'live';
  const region = flags.region || process.env.AWS_REGION || 'us-east-1';
  const toVersion = flags['to-version']; // optional explicit version

  log.hdr(`Rollback · ${fn} alias ${aliasName} · ${apply ? color.red('APPLY') : color.yellow('DRY-RUN')}`);

  const Lambda = await import('@aws-sdk/client-lambda');
  const client = new Lambda.LambdaClient({ region });

  const alias = await client.send(new Lambda.GetAliasCommand({ FunctionName: fn, Name: aliasName }));
  const current = alias.FunctionVersion;
  log.info(`current alias → version ${current}`);

  let target = toVersion;
  if (!target) {
    // enumerate versions, pick the one just below current
    const versions = [];
    let Marker;
    do {
      const resp = await client.send(new Lambda.ListVersionsByFunctionCommand({ FunctionName: fn, Marker }));
      for (const v of resp.Versions || []) {
        if (v.Version !== '$LATEST' && v.Version !== current) versions.push(Number(v.Version));
      }
      Marker = resp.NextMarker;
    } while (Marker);
    if (versions.length === 0) throw new Error('No prior numbered version exists — cannot rollback.');
    versions.sort((a, b) => b - a);
    const candidate = versions.find(v => v < Number(current)) ?? versions[0];
    target = String(candidate);
  }
  log.info(`target version → ${target}`);

  if (!apply) {
    log.warn('Dry-run. Pass --apply to roll back.');
    return;
  }

  await client.send(new Lambda.UpdateAliasCommand({
    FunctionName: fn, Name: aliasName, FunctionVersion: target, RoutingConfig: {},
  }));
  log.ok(`rolled ${fn}@${aliasName} → ${target}`);
}