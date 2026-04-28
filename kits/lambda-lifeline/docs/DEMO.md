# Lambda Lifeline — End-to-End Demo Transcript

Captured: Tue Apr 28 09:30:11 UTC 2026

```
1.0.0

$ lambda-lifeline scan --fixture test/fixtures/lambda-inventory.json

▸ Scanning fixture: test/fixtures/lambda-inventory.json
ℹ Scanned 6 functions · 1 healthy · 5 at risk

Function                             Runtime        Region         Severity           Days   Target
---------------------------------------------------------------------------------------------------
api-orders-ingest                    nodejs20.x     us-east-1      high               154    nodejs22.x
billing-webhook-processor            nodejs18.x     us-east-1      high               154    nodejs22.x
legacy-cron-cleanup                  nodejs16.x     us-west-2      high               154    nodejs22.x
report-generator                     python3.10     us-east-1      medium             261    python3.12
ruby-legacy-processor                ruby3.2        us-east-1      high               154    ruby3.4

⚠ Next: run `lambda-lifeline codemod --path <your-repo>` then `audit`, `iac`, and `deploy`.

$ lambda-lifeline codemod --path examples/sample-app

▸ Codemod: DRY-RUN · examples/sample-app
⚠ No files will be written. Pass --apply to execute.
  2 source file(s) found
ℹ [rewrite] examples/sample-app/src/handler.mjs · assert-to-with · 2 hit(s)
ℹ [rewrite] examples/sample-app/src/handler.mjs · dynamic-import-assert · 1 hit(s)
ℹ [lint] examples/sample-app/src/handler.mjs · buffer-negative-index · 1 hit(s)

✓ 1 file(s) with 4 edit(s). Preview only.
⚠ 1 lint finding(s) need human review (cannot auto-fix safely).

$ lambda-lifeline audit --path examples/sample-app

▸ Audit native dependencies · examples/sample-app/package.json
  ⚠ sharp                        UPGRADE    declared 0.32.6  →  need ≥ 0.33.0
     libvips native binding. v0.33+ ships Node 22 prebuilds.
  ⚠ bcrypt                       UPGRADE    declared 5.0.1  →  need ≥ 5.1.1
     Native bcrypt. Consider bcryptjs for pure-JS drop-in.
  ⚠ better-sqlite3               UPGRADE    declared 10.0.0  →  need ≥ 11.0.0
     SQLite native binding.
  ✗ node-sass                    DEAD       drop this dep
     DEAD. Use `sass` (Dart Sass) instead — no native deps.
  ✗ grpc                         DEAD       drop this dep
     DEAD. Migrate to `@grpc/grpc-js` (pure JS).

⚠ 5 native dep(s) need action before Node 22.
ℹ Next: bump versions in package.json, run `npm install && npm rebuild`, then `npm test`.

$ lambda-lifeline iac --path examples/sample-app

▸ IaC patcher · examples/sample-app · nodejs16.x,nodejs18.x,nodejs20.x → nodejs22.x · DRY-RUN
  scanning 8 candidate file(s)
ℹ [CDK] examples/sample-app/cdk/stack.ts · 2 runtime ref(s): NODEJS_18_X, NODEJS_20_X
ℹ [Terraform] examples/sample-app/infra/main.tf · 2 runtime ref(s): nodejs20.x, nodejs18.x
ℹ [SAM/CFN] examples/sample-app/template.yaml · 3 runtime ref(s): nodejs20.x, nodejs18.x, nodejs16.x

✓ 3 file(s) · 7 runtime ref(s) would be updated.
ℹ Re-run with --apply to write changes. Review diff with `git diff`.

$ lambda-lifeline plan --function orders-ingest

▸ Deploy plan for orders-ingest
   1. Snapshot current live version (LATEST_STABLE tag)
   2. Update function runtime → nodejs22.x
   3. Publish new version (N+1)
   4. Create/update alias "live" with weighted routing
   5. Shift 5% of traffic to N+1 · hold 10 min · check alarms
   6. Shift 25% of traffic to N+1 · hold 10 min · check alarms
   7. Shift 50% of traffic to N+1 · hold 10 min · check alarms
   8. Shift 100% of traffic to N+1 · hold 10 min · check alarms
   9. Cut alias entirely to N+1 once 100% stable
  10. On any alarm trip: auto-rollback alias to LATEST_STABLE and halt
ℹ Run with `deploy --apply` to execute.
```
