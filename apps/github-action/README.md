# `rupture/check` — GitHub Action

Free GitHub Action that scans your IaC and source for AWS runtime deprecation issues, annotates the PR, and links to the paid Audit PDF for the deeper report.

## Usage

```yaml
- uses: ntoledo319/Rupture/apps/github-action@v1
  with:
    kit: auto          # or: lambda-lifeline | al2023-gate | python-pivot
    path: .
    format: markdown
    fail-on: high
    comment-pr: true
```

## Inputs

See `action.yml`. All optional with sensible defaults.

## What it does

- Auto-detects the relevant kit from your repo's file mix (Node.js → `lambda-lifeline`, Python → `python-pivot`, AMI/Packer/AL2 IaC → `al2023-gate`).
- Runs the kit in the workspace.
- Comments findings on the PR (configurable).
- Fails the check on `--fail-on` severity (default: `high`).

## What it does NOT do

- It does not modify your code. Use the paid **Migration Pack** (`https://ntoledo319.github.io/Rupture/pack/`) for that.
- It does not send any data outside the runner — no telemetry, no remote calls beyond `pip install`.

## Pricing

The Action is free. The Audit PDF (`/audit`) and Migration Pack (`/pack`) are paid.
