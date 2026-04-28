// Staged canary deploy with rollback guard.
//   1. Publishes a new Lambda version with the new runtime
//   2. Routes traffic to it via a weighted alias
//   3. Steps through stages (e.g. 5% → 25% → 50% → 100%)
//   4. At each stage, verifies a CloudWatch alarm ARN is NOT in ALARM state
//   5. If any alarm trips, auto-rollback to previous version
//
// Dry-run prints the plan. --apply executes.

import { parseArgs, isDryRun, requireFlag, list } from '../util/args.mjs';
import { log, color } from '../util/log.mjs';
import { setTimeout as sleep } from 'node:timers/promises';

const DEFAULT_STAGES = [5, 25, 50, 100];

export async function planCommand(argv) {
  const { flags } = parseArgs(argv);
  const fn = requireFlag(flags, 'function');
  const newRuntime = flags['new-runtime'] || 'nodejs22.x';
  const stages = list(flags.stages).map(Number).filter(n => n > 0);
  const plan = buildPlan({ fn, newRuntime, stages: stages.length ? stages : DEFAULT_STAGES, wait: Number(flags['wait-minutes'] || 10) });
  log.hdr(`Deploy plan for ${color.bold(fn)}`);
  for (const step of plan) {
    console.log(`  ${color.cyan(String(step.n).padStart(2))}. ${step.desc}`);
  }
  log.info('Run with `deploy --apply` to execute.');
}

function buildPlan({ fn, newRuntime, stages, wait }) {
  const steps = [];
  steps.push({ n: 1, desc: `Snapshot current live version (LATEST_STABLE tag)` });
  steps.push({ n: 2, desc: `Update function runtime → ${newRuntime}` });
  steps.push({ n: 3, desc: `Publish new version (N+1)` });
  steps.push({ n: 4, desc: `Create/update alias "live" with weighted routing` });
  let s = 5;
  for (const weight of stages) {
    steps.push({ n: s++, desc: `Shift ${weight}% of traffic to N+1 · hold ${wait} min · check alarms` });
  }
  steps.push({ n: s++, desc: `Cut alias entirely to N+1 once 100% stable` });
  steps.push({ n: s, desc: `On any alarm trip: auto-rollback alias to LATEST_STABLE and halt` });
  return steps;
}

export async function deployCommand(argv) {
  const { flags } = parseArgs(argv);
  const apply = !isDryRun(flags);
  const fn = requireFlag(flags, 'function');
  const newRuntime = flags['new-runtime'] || 'nodejs22.x';
  const aliasName = flags.alias || 'live';
  const stages = (list(flags.stages).map(Number).filter(n => n > 0)) ;
  const stagesList = stages.length ? stages : DEFAULT_STAGES;
  const waitMinutes = Number(flags['wait-minutes'] || 10);
  const alarms = list(flags.alarm);
  const region = flags.region || process.env.AWS_REGION || 'us-east-1';

  log.hdr(`Deploy · ${fn} → ${newRuntime} · ${apply ? color.red('APPLY') : color.yellow('DRY-RUN')}`);
  if (!apply) {
    const plan = buildPlan({ fn: fn, newRuntime, stages: stagesList, wait: waitMinutes });
    for (const p of plan) console.log(`  ${color.cyan(p.n)}. ${p.desc}`);
    log.warn('Dry-run complete. Pass --apply (and --alarm <cw-alarm-arn>) to execute.');
    return;
  }

  if (alarms.length === 0) {
    throw new Error('--apply requires at least one --alarm <CloudWatchAlarmArn> for the rollback guard.');
  }

  const Lambda = await import('@aws-sdk/client-lambda');
  const CW = await import('@aws-sdk/client-cloudwatch');
  const lambda = new Lambda.LambdaClient({ region });
  const cw = new CW.CloudWatchClient({ region });

  log.info('1. Snapshotting current live version…');
  const currentAlias = await safe(() =>
    lambda.send(new Lambda.GetAliasCommand({ FunctionName: fn, Name: aliasName }))
  );
  const stableVersion = currentAlias?.FunctionVersion || '$LATEST';
  log.dim(`   LATEST_STABLE = ${stableVersion}`);

  log.info(`2. Updating function runtime → ${newRuntime}…`);
  await lambda.send(new Lambda.UpdateFunctionConfigurationCommand({
    FunctionName: fn,
    Runtime: newRuntime,
  }));
  await waitForUpdate(lambda, Lambda, fn);

  log.info('3. Publishing new version…');
  const published = await lambda.send(new Lambda.PublishVersionCommand({ FunctionName: fn }));
  const newVersion = published.Version;
  log.ok(`   Published version ${newVersion}`);

  log.info(`4. Creating/updating alias "${aliasName}"…`);
  try {
    await lambda.send(new Lambda.CreateAliasCommand({
      FunctionName: fn, Name: aliasName, FunctionVersion: stableVersion,
    }));
  } catch (e) {
    if (e.name !== 'ResourceConflictException') throw e;
  }

  for (const weight of stagesList) {
    const pct = weight / 100;
    log.info(`5. Shifting ${weight}% traffic to version ${newVersion}…`);
    await lambda.send(new Lambda.UpdateAliasCommand({
      FunctionName: fn,
      Name: aliasName,
      FunctionVersion: stableVersion,
      RoutingConfig: weight === 100 ? undefined : { AdditionalVersionWeights: { [newVersion]: pct } },
    }));
    if (weight === 100) {
      await lambda.send(new Lambda.UpdateAliasCommand({
        FunctionName: fn, Name: aliasName, FunctionVersion: newVersion, RoutingConfig: {},
      }));
      log.ok('   100% cutover complete.');
      break;
    }
    log.dim(`   holding ${waitMinutes} min — checking alarms every minute…`);
    for (let minute = 0; minute < waitMinutes; minute++) {
      await sleep(apply ? 60_000 : 50);
      const tripped = await checkAlarms(cw, CW, alarms);
      if (tripped.length) {
        log.err(`ALARM TRIPPED: ${tripped.join(', ')} — rolling back to ${stableVersion}`);
        await lambda.send(new Lambda.UpdateAliasCommand({
          FunctionName: fn, Name: aliasName, FunctionVersion: stableVersion, RoutingConfig: {},
        }));
        log.ok('rollback complete');
        process.exit(1);
      }
    }
  }
  log.ok('Deployment complete. Run `lambda-lifeline rollback --function ' + fn + '` if issues surface later.');
}

async function checkAlarms(cw, CW, arns) {
  const names = arns.map(a => a.split(':alarm:').pop()).filter(Boolean);
  if (names.length === 0) return [];
  const resp = await cw.send(new CW.DescribeAlarmsCommand({ AlarmNames: names, StateValue: 'ALARM' }));
  return (resp.MetricAlarms || []).map(a => a.AlarmName);
}

async function waitForUpdate(client, Lambda, fn) {
  for (let i = 0; i < 60; i++) {
    const cfg = await client.send(new Lambda.GetFunctionConfigurationCommand({ FunctionName: fn }));
    if (cfg.LastUpdateStatus === 'Successful') return;
    if (cfg.LastUpdateStatus === 'Failed') throw new Error(`Update failed: ${cfg.LastUpdateStatusReason}`);
    await sleep(2000);
  }
  throw new Error('Timed out waiting for function update to settle.');
}

async function safe(fn) { try { return await fn(); } catch { return null; } }