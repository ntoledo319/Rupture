# Migrating AWS Lambda Node.js 20 to Node.js 22: A complete guide (Apr 30, 2026 EOL)

> Published 2026-04-28. For teams running AWS Lambda functions on `nodejs20.x`. Source: [AWS Lambda runtimes official docs](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html).

## TL;DR

- **April 30, 2026**: AWS stops security patches for `nodejs20.x` (Phase 1).
- **August 31, 2026**: AWS blocks creating *new* functions on `nodejs20.x` (Phase 2).
- **September 30, 2026**: AWS blocks *updating* existing functions on `nodejs20.x` (Phase 3, the hard cliff).
- Migrating to `nodejs22.x` is a semver-breaking change. Most code works. A specific set of patterns will break. This post documents all of them.
- We built an open-source CLI called [`lambda-lifeline`](https://github.com/ntoledo319/Rupture/tree/main/kits/lambda-lifeline) that automates the whole migration: scan, codemod, audit, IaC patch, canary deploy with auto-rollback.

---

## Why this is happening

AWS runs a 3-phase deprecation process for every Lambda runtime. Phase 1 ends security patches. Phase 2 blocks creating new functions on the deprecated runtime. Phase 3 blocks *updating* existing functions. The phases are always spaced ~3-4 months apart, and once Phase 3 hits, your only option is a full deploy with a new runtime.

Node.js 20 itself is officially supported by the Node.js Foundation until April 2026 ([Node.js release schedule](https://github.com/nodejs/release#release-schedule)). AWS Lambda aligns to the upstream EOL date, so April 30, 2026 is the start of the 3-phase countdown.

Node.js 22 is the next LTS. Upstream maintenance continues until April 2027. That's the target runtime.

---

## The breaking changes between Node.js 20 and Node.js 22

These are the patterns that actually trip migrations. Most Node 20 code runs on Node 22 unchanged — these are the exceptions.

### 1. Import assertions → import attributes

Node 20 accepted the stage-3 TC39 proposal syntax:

```javascript
// Node 20 — valid
import config from './config.json' assert { type: 'json' };

const schema = await import('./schema.json', { assert: { type: 'json' } });
```

Node 22 implements the finalized stage-4 spec, which renamed `assert` to `with`:

```javascript
// Node 22 — valid
import config from './config.json' with { type: 'json' };

const schema = await import('./schema.json', { with: { type: 'json' } });
```

The old syntax is a hard parse error in Node 22. Every JSON import and every CSS/WASM import statement in your codebase needs rewriting. This is the #1 breakage pattern.

### 2. Native binding ABI bumps

Anything with a native `.node` binary needs a rebuild or a version bump. The packages that actually ship native bindings and historically lag:

| Package | Minimum Node 22-compatible version |
|---|---|
| `sharp` | `0.33.0` |
| `bcrypt` | `5.1.1` |
| `better-sqlite3` | `11.0.0` |
| `canvas` | `2.11.2` |
| `node-sass` | — *(dead project, switch to `sass`)* |
| `grpc` | — *(dead, use `@grpc/grpc-js`)* |
| `fibers` | — *(dead, use native async)* |

If your `package.json` pins any of these below the minimum, `npm install` on Node 22 will either fail to compile or crash at runtime.

### 3. CA certificate loading

Node 22 changed how custom CAs are loaded. If you set `NODE_EXTRA_CA_CERTS` on your Lambda environment, nothing changes — it still works. If you were relying on the old bundled cert store behavior without setting that env var, TLS connections to private CAs will suddenly fail. The fix is to always set `NODE_EXTRA_CA_CERTS=/etc/pki/ca-trust/source/anchors/your-ca.pem` in the function environment.

### 4. `Buffer.prototype.toString()` negative indices

Node 20 silently tolerated negative `start`/`end` arguments. Node 22 throws `RangeError`. If you have:

```javascript
buf.toString('utf8', -10, -1);
```

That's now a runtime error. Switch to:

```javascript
buf.toString('utf8', Math.max(0, buf.length - 10), buf.length - 1);
```

### 5. Streams `highWaterMark` default change

The default highWaterMark for object-mode streams dropped from 16 to 1. If you had code depending on backpressure thresholds, revisit it.

### 6. `url.parse()` is deprecated harder

Still works, but now emits a warning per call. If your CloudWatch logs hit warning thresholds, this is worth rewriting. Use `new URL(...)` instead.

---

## The migration surface

For a typical medium-sized company, you have:

1. **Function source code** — the handlers themselves, plus any JS libraries they import
2. **`package.json`** — dependency versions, especially native bindings
3. **Infrastructure as Code** — SAM templates, CDK stacks, Terraform config, or Serverless Framework `serverless.yml`
4. **CI/CD pipelines** — any `Runtime` references in GitHub Actions, CircleCI, GitLab
5. **Docker base images** — if you use container Lambdas, the base image tag needs updating

Tracking all of this by hand is where migrations stall.

---

## Step-by-step migration

### Step 1: Inventory

Find every Lambda function on a deprecated runtime across every region. AWS doesn't give you this in one API call — you have to paginate through `ListFunctions` per region.

```bash
# With lambda-lifeline
npx lambda-lifeline scan --regions us-east-1,us-east-2,eu-west-1 --format json --out inventory.json

# With plain AWS CLI
for region in us-east-1 us-east-2 eu-west-1; do
  aws lambda list-functions --region $region \
    --query "Functions[?contains(Runtime, 'nodejs') && Runtime != 'nodejs22.x'].[FunctionName,Runtime,LastModified]" \
    --output table
done
```

You will almost certainly find functions nobody on your team remembers deploying.

### Step 2: Codemod the source

For the `import assert` → `import with` change, the naive sed approach:

```bash
find . -name '*.js' -o -name '*.mjs' -o -name '*.ts' | \
  xargs sed -i 's/assert { type:/with { type:/g'
```

This over-triggers on `assert(...)` function calls. Use a proper AST tool or [`lambda-lifeline codemod`](https://github.com/ntoledo319/Rupture/tree/main/kits/lambda-lifeline) which only matches the import-assertion grammar.

```bash
npx lambda-lifeline codemod src/ --apply
```

### Step 3: Audit `package.json` native bindings

Run through your direct and transitive dependencies and check each one's Node 22 compatibility:

```bash
npx lambda-lifeline audit package.json
```

Output:

```
[high] sharp declared=^0.31.0 · needs >=0.33.0
[high] bcrypt declared=^5.0.0 · needs >=5.1.1
[critical] node-sass declared=^6.0.1 · no Node 22 support (dead project)
```

### Step 4: Patch IaC

For SAM templates:

```yaml
# Before
Runtime: nodejs20.x
# After
Runtime: nodejs22.x
```

For CDK (TypeScript):

```typescript
// Before
runtime: lambda.Runtime.NODEJS_20_X,
// After
runtime: lambda.Runtime.NODEJS_22_X,
```

For Terraform:

```hcl
# Before
runtime = "nodejs20.x"
# After
runtime = "nodejs22.x"
```

The `lambda-lifeline iac` command handles all four formats (SAM, CDK, Terraform, Serverless) including CloudFormation `Globals:` blocks and CDK enum references.

```bash
npx lambda-lifeline iac infrastructure/ --apply
```

### Step 5: Stage a canary deploy

The critical step. Do not cut over atomically. Use Lambda versions + weighted alias routing:

1. Publish a new version with the Node 22 runtime
2. Record the current stable version
3. Route 5% of traffic to the new version for ~60s, check CloudWatch alarms
4. Route 25%, wait, check
5. Route 50%, wait, check
6. Route 100%, done

If any alarm trips at any stage, auto-rollback the alias to the stable version:

```bash
npx lambda-lifeline deploy \
  --function payment-webhook \
  --alias live \
  --stages 5,25,50,100 \
  --dwell 60 \
  --alarm arn:aws:cloudwatch:us-east-1:1234:alarm:PaymentErrors \
  --apply
```

The `--alarm` flag is required when `--apply` is set. No alarm, no deploy.

### Step 6: Rollback plan

Always have a tested rollback. Manual rollback is just re-pointing the alias:

```bash
npx lambda-lifeline rollback --function payment-webhook --alias live --apply
```

Or with plain AWS CLI:

```bash
aws lambda update-alias \
  --function-name payment-webhook \
  --name live \
  --function-version 47    # previous stable
```

---

## What to check after migration

- **Cold-start time**: Node 22 is typically 5-15% faster than Node 20 in Lambda. If yours is slower, it's a native binding issue.
- **Memory usage**: generally flat, sometimes 1-3% lower.
- **Invocation error rate**: should be identical. Any spike = native binding incompat.
- **CloudWatch Logs for deprecation warnings**: `(node:123) [DEP0XXX] DeprecationWarning: ...`. Clean these up before the next LTS.

---

## Why we built `lambda-lifeline`

We kept getting the same "your runtime is deprecated" email from AWS every 6-8 months. Each time, the migration work was unglamorous, had huge blast radius, and had no integrated tool. CloudQuery gives you inventory. AWS Migration Hub is for cross-region lift-and-shift. aws-samples gives you snippets. Nothing combined scan + codemod + IaC patch + tested deploy + rollback for a specific deprecation.

So we scoped it. `lambda-lifeline` only migrates Node.js Lambda runtimes. It does nothing else. It has 24 tests covering every command, every output format, every exit-code path. It defaults to dry-run. The canary deploy refuses to run without an alarm ARN.

Source: https://github.com/ntoledo319/Rupture/tree/main/kits/lambda-lifeline

It's MIT-licensed. Fork it, use it, resell it.

---

## Related guides

- [Migrating Amazon Linux 2 to AL2023](https://github.com/ntoledo319/Rupture/tree/main/kits/al2023-gate) — deadline June 30, 2026
- [Migrating Lambda Python 3.9/3.10 to 3.12](https://github.com/ntoledo319/Rupture/tree/main/kits/python-pivot) — Python 3.9 already past EOL

---

*If you work at a company that runs Lambda on Node 20 and needs help migrating, the `lambda-lifeline` kit is free. The [Team and Enterprise tiers](https://sites.super.myninja.ai/a51b9893-5170-4e08-87ed-c7db56f6885b/0eb07112/index.html) add a printable PDF runbook, a captioned video walkthrough, expanded dependency tables, custom codemod rules for your codebase, and priority Slack support.*