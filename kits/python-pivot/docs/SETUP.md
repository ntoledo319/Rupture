# python-pivot — 30-minute setup

## 0. Prereqs

- Python 3.9+
- AWS creds with Lambda read permissions (for live scan) + Lambda write + CloudWatch read (for deploy/rollback)

## 1. Install

```bash
git clone https://github.com/ntoledo319/Rupture.git
cd Rupture/kits/python-pivot
pip install -e '.[aws]'

python-pivot --help
python-pivot --version
```

## 2. Scan your account

```bash
# single region
python-pivot scan --regions us-east-1

# multi-region, JSON for CI
python-pivot scan --regions us-east-1,us-east-2,eu-west-1 --format json --out functions.json

# strict mode for CI
python-pivot scan --regions us-east-1 --strict
```

## 3. Codemod your source

```bash
# always dry-run first
python-pivot codemod src/

# then apply
python-pivot codemod src/ --apply

# review changes
git diff src/
```

## 4. Audit requirements

```bash
python-pivot audit requirements.txt
python-pivot audit requirements.txt --strict    # for CI
python-pivot audit requirements.txt --format json > wheel-audit.json
```

For each `high` or `critical` finding, update the pin in `requirements.txt` and re-run.

## 5. Patch your IaC

```bash
python-pivot iac infra/ --apply
git diff infra/
```

## 6. Create a CloudWatch alarm (if you don't already have one)

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name PaymentWebhookErrors \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 60 \
  --evaluation-periods 2 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=payment-webhook
```

## 7. Deploy

```bash
# plan first
python-pivot deploy --function payment-webhook --plan-only

# then execute
python-pivot deploy \
  --function payment-webhook \
  --alias live \
  --stages 5,25,50,100 \
  --dwell 60 \
  --alarm PaymentWebhookErrors \
  --apply
```

## 8. Rollback (if needed)

```bash
python-pivot rollback --function payment-webhook --alias live --apply
```

## CI integration

`.github/workflows/python-pivot.yml`:

```yaml
name: Python 3.12 readiness
on: [pull_request]

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install python-pivot
      - run: python-pivot codemod src/ --strict
      - run: python-pivot audit requirements.txt --strict
      - run: python-pivot iac infra/ --strict
      - name: Live scan (read-only)
        env:
          AWS_REGION: us-east-1
          AWS_ACCESS_KEY_ID: ${{ secrets.READONLY_KEY }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.READONLY_SECRET }}
        run: python-pivot scan --regions us-east-1 --strict
```