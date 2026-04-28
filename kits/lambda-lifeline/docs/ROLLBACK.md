# Rollback Playbook

When a Node 22 deployment misbehaves in production, these are the procedures in priority order. Every procedure is non-destructive — your existing Lambda versions are immutable, so every rollback is an alias pointer change that takes effect in ~1 second.

## 0. Know which alias you deployed to

Every safe deployment from `lambda-lifeline` uses a **named alias** (default: `live`). Your callers (API Gateway, EventBridge, etc.) should invoke the alias ARN, not `$LATEST`, or this playbook doesn't apply.

Check:
```bash
aws lambda get-alias --function-name FN --name live
# .FunctionVersion should be a number like "17", not "$LATEST"
```

## 1. Canary phase — automatic

If `lambda-lifeline deploy --apply --alarm …` was running when the problem surfaced, the kit will have already reverted the alias to the previous stable version automatically. You will see:

```
✗ ALARM TRIPPED: fn-5xx-alarm — rolling back to 16
✓ rollback complete
```

Verify:
```bash
aws lambda get-alias --function-name FN --name live
# FunctionVersion: 16  (the pre-deploy version)
```

No further action needed. Re-run the kit after fixing the root cause.

## 2. Post-cutover — within minutes

If the 100% cutover completed, alarms didn't trip, but your engineers are now reporting issues:

```bash
lambda-lifeline rollback --function FN --apply
# rolls to N-1 automatically
```

Or to a specific prior version:

```bash
lambda-lifeline rollback --function FN --to-version 16 --apply
```

Behind the scenes this is:
```bash
aws lambda update-alias --function-name FN --name live --function-version 16
```

## 3. Cold-storage rollback — hours later, across many functions

If you ran the migration on dozens of functions, and need to revert all of them:

```bash
# Scan what you migrated
aws lambda list-functions --query "Functions[?Runtime=='nodejs22.x'].FunctionName" --output text | \
  tr '\t' '\n' | while read fn; do
    lambda-lifeline rollback --function "$fn" --apply
  done
```

Keep a migration manifest (from `scan --out scan.json`) so you know exactly which functions are in play.

## 4. Runtime rollback — last resort

Aliases can't cross a runtime boundary if the old version doesn't exist. If you deleted old versions, you must:

1. Re-deploy the old code with the old runtime:
   ```bash
   aws lambda update-function-configuration --function-name FN --runtime nodejs20.x
   aws lambda update-function-code        --function-name FN --zip-file fileb://old.zip
   aws lambda publish-version             --function-name FN
   ```
2. Point alias at new published version.

**Note:** After **August 31, 2026** you cannot create functions on `nodejs20.x` at all, and after **September 30, 2026** you cannot update them. Rollbacks to EOL runtimes become impossible past these dates — this is why version pinning + alias-based deploys matter.

## 5. Dependency rollback

If native modules crash with `NODE_MODULE_VERSION` mismatch after deploy:

```bash
# In your app repo
git revert <migration-commit>
npm install
npm rebuild
# re-package & deploy the original
```

## Canary alarm setup (recommended)

Every `lambda-lifeline deploy --apply` requires at least one CloudWatch alarm ARN. Create one per function before deploying:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name lambda-lifeline-FN-errors \
  --metric-name Errors --namespace AWS/Lambda \
  --statistic Sum --period 60 --evaluation-periods 2 \
  --threshold 5 --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=FN
```