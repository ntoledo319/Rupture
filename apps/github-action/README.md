# `rupture/check` — GitHub Action

Free GitHub Action that scans your IaC and source for AWS runtime deprecation issues, annotates the PR, and links to the paid Audit PDF for the deeper report.

## Usage

```yaml
- uses: ntoledo319/Rupture@v1
  with:
    kit: auto          # or: all | lambda-lifeline | al2023-gate | python-pivot
    path: .
    format: markdown
    fail-on: high
    comment-pr: true
```

## Inputs

See `action.yml`. All optional with sensible defaults.

## What it does

- Runs the path-safe checks from all kits in dry-run mode by default (`auto`/`all`).
- Uses `lambda-lifeline` for Node.js and Lambda IaC, `python-pivot` for Python 3.12 readiness, and `al2023-gate` for AL2023 Ansible/cloud-init risk.
- Comments findings on the PR (configurable).
- Fails the check on `--fail-on` severity (default: `high`).

## What it does NOT do

- It does not modify your code. Use the paid **Migration Pack** (`https://ntoledo319.github.io/Rupture/pack/`) for that.
- It does not send any data outside the runner. Install traffic is limited to GitHub Actions setup actions plus local package installs from the checked-out action source.

## Pricing

The Action is free. The Audit PDF (`/audit`) and Migration Pack (`/pack`) are paid.
