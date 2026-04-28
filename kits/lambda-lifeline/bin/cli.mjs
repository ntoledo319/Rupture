#!/usr/bin/env node
// lambda-lifeline CLI — https://github.com/ntoledo319/lambda-lifeline
// Rupture Kits · MIT · safe for production use (all mutations gated behind --apply)

import { scanCommand } from '../src/scan/index.mjs';
import { codemodCommand } from '../src/codemod/index.mjs';
import { auditCommand } from '../src/deps/index.mjs';
import { certsCommand } from '../src/certs/index.mjs';
import { iacCommand } from '../src/iac/index.mjs';
import { planCommand, deployCommand } from '../src/deploy/index.mjs';
import { rollbackCommand } from '../src/rollback/index.mjs';

const BANNER = `
 ╔══════════════════════════════════════════════════════════════╗
 ║  lambda-lifeline · AWS Lambda Node.js 20 EOL Migration Kit   ║
 ║  Deadlines: Apr 30, 2026 (patches) · Sep 30, 2026 (updates)  ║
 ║  https://github.com/ntoledo319/lambda-lifeline · MIT         ║
 ╚══════════════════════════════════════════════════════════════╝
`;

const HELP = `${BANNER}
USAGE
  lambda-lifeline <command> [options]

COMMANDS
  scan       Scan all AWS accounts/regions for Node 16/18/20 Lambda functions
             Flags: --regions us-east-1,us-west-2  --profile <aws-profile>  --json  --out scan.json

  codemod    Rewrite code for Node.js 22 compatibility
             Flags: --path <dir>  --apply  --rules assert-to-with,buffer-safety,streams-hwm
             (default: --dry-run — prints a diff, writes nothing)

  audit      Audit package.json for native binary ABI risk
             Flags: --path <dir>  --json  --strict
             Exit 1 on unresolved risks; prints upgrade hints

  certs      Patch functions that need NODE_EXTRA_CA_CERTS for RDS/Amazon services
             Flags: --function <name>  --all  --apply

  iac        Patch IaC files (SAM template.yaml, CDK, Terraform)
             Flags: --path <dir>  --from nodejs20.x  --to nodejs22.x  --apply

  plan       Print a staged canary deploy plan (versions → alias → weighted routing)
             Flags: --function <name>  --stages 5,25,50,100  --wait-minutes 10

  deploy     Execute staged canary deploy with auto-rollback on alarm
             Flags: --function <name>  --new-runtime nodejs22.x  --apply
             (default: --dry-run. Requires CloudWatch alarm ARNs via --alarm)

  rollback   Roll function alias back to previous version
             Flags: --function <name>  --alias live  --apply

  help       Show this message

ENVIRONMENT
  AWS_PROFILE, AWS_REGION — standard AWS SDK resolution
  LAMBDA_LIFELINE_DRY_RUN=1 — force dry-run everywhere

EXAMPLES
  # 1. Inventory
  lambda-lifeline scan --regions us-east-1,us-west-2 --out scan.json

  # 2. Fix code (dry-run then apply)
  lambda-lifeline codemod --path ./src
  lambda-lifeline codemod --path ./src --apply

  # 3. Audit deps
  lambda-lifeline audit --path . --strict

  # 4. Patch SAM template
  lambda-lifeline iac --path ./infra --apply

  # 5. Staged deploy with rollback guard
  lambda-lifeline deploy --function my-fn --apply \\
      --alarm arn:aws:cloudwatch:us-east-1:123:alarm:fn-errors

DOCS · https://github.com/ntoledo319/lambda-lifeline#readme
`;

const args = process.argv.slice(2);
const cmd = args[0];

async function main() {
  try {
    switch (cmd) {
      case 'scan':     return await scanCommand(args.slice(1));
      case 'codemod':  return await codemodCommand(args.slice(1));
      case 'audit':    return await auditCommand(args.slice(1));
      case 'certs':    return await certsCommand(args.slice(1));
      case 'iac':      return await iacCommand(args.slice(1));
      case 'plan':     return await planCommand(args.slice(1));
      case 'deploy':   return await deployCommand(args.slice(1));
      case 'rollback': return await rollbackCommand(args.slice(1));
      case 'help':
      case '--help':
      case '-h':
      case undefined:
        console.log(HELP);
        return;
      case '--version':
      case '-v': {
        const pkg = JSON.parse(
          await (await import('node:fs/promises')).readFile(
            new URL('../package.json', import.meta.url),
            'utf8'
          )
        );
        console.log(pkg.version);
        return;
      }
      default:
        console.error(`Unknown command: ${cmd}\n`);
        console.log(HELP);
        process.exit(2);
    }
  } catch (err) {
    console.error(`\nāœ— ${err.message}`);
    if (process.env.DEBUG) console.error(err.stack);
    process.exit(1);
  }
}

main();