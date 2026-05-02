# Direct Support Thread Answers

Use these only when the thread is already about the exact migration problem.
Lead with the useful fix, disclose affiliation, and avoid repeating the same
reply across communities.

## Search Queries

### Lambda Node.js Runtime Migration

```
site:stackoverflow.com/questions AWS Lambda Node.js 20 Node.js 22 migration
site:repost.aws/questions Lambda Node.js 20 runtime Node.js 22
site:github.com/issues lambda nodejs20.x nodejs22.x
"lambda" "nodejs20.x" "nodejs22.x" "import assertions"
"AWS Lambda" "Node.js 20" "deprecated runtime"
```

### Amazon Linux 2 To AL2023

```
site:stackoverflow.com/questions "Amazon Linux 2" "AL2023" migration
site:repost.aws/questions "Amazon Linux 2" "AL2023" "launch template"
site:github.com/issues "amazon linux 2" "al2023" "yum" "dnf"
"EKS" "Amazon Linux 2" "AL2023" node group migration
"Elastic Beanstalk" "Amazon Linux 2" "AL2023"
```

### Lambda Python Runtime Migration

```
site:stackoverflow.com/questions "AWS Lambda" "python3.9" "python3.12"
site:repost.aws/questions "Lambda Python 3.10" "Python 3.12"
site:github.com/issues "python3.11" "python3.12" "AWS Lambda"
"Lambda" "Python 3.12" "distutils"
"Lambda" "Python 3.12" "native wheels"
```

## Reply Template: Lambda Node.js

You are probably dealing with two separate migration surfaces:

1. Runtime declaration updates in IaC (`nodejs20.x` to `nodejs22.x`).
2. Code/package compatibility, especially import assertions and native modules
   like `sharp`, `bcrypt`, `canvas`, or `sqlite3`.

A safe sequence is:

```bash
npx lambda-lifeline scan --format table
npx lambda-lifeline codemod --path . --dry-run
npx lambda-lifeline audit --path package.json
npx lambda-lifeline iac --path . --target nodejs22.x --dry-run
```

Then run the deploy as a canary behind a CloudWatch alarm instead of flipping
all traffic at once.

Disclosure: I maintain Rupture, an MIT-licensed set of AWS deprecation CLIs.
The relevant kit is `lambda-lifeline`: https://github.com/ntoledo319/Rupture/tree/main/kits/lambda-lifeline

## Reply Template: Amazon Linux 2

Treat this as more than an AMI replacement. The usual breakpoints are package
name changes, `yum` to `dnf`, cloud-init assumptions, launch template drift,
and EKS/ECS/Beanstalk platform-specific rollout behavior.

A practical first pass:

```bash
python -m al2023_gate scan --format table
python -m al2023_gate remap --packages packages.txt
python -m al2023_gate cloudinit --path user-data.yaml --dry-run
python -m al2023_gate runbook --target eks
```

For ASGs, create a new launch template version and roll one instance class at a
time. For EKS, prefer a parallel node group and drain gradually.

Disclosure: I maintain Rupture, an MIT-licensed set of AWS deprecation CLIs.
The relevant kit is `al2023-gate`: https://github.com/ntoledo319/Rupture/tree/main/kits/al2023-gate

## Reply Template: Lambda Python

The runtime flag is usually the easy part. The risky parts are removed stdlib
APIs (`distutils`, old `collections` imports), `datetime.utcnow()` behavior,
asyncio changes, and package wheels that do not exist for cp312.

Suggested sequence:

```bash
python -m python_pivot scan --format table
python -m python_pivot codemod --path . --dry-run
python -m python_pivot audit requirements.txt
python -m python_pivot iac --path . --target python3.12 --dry-run
```

Do not deploy until the requirements audit is clean or every native dependency
has a known cp312-compatible build.

Disclosure: I maintain Rupture, an MIT-licensed set of AWS deprecation CLIs.
The relevant kit is `python-pivot`: https://github.com/ntoledo319/Rupture/tree/main/kits/python-pivot

## Short GitHub Issue Reply

This looks like the same migration class Rupture targets. The key is to separate
inventory, codemod, IaC patching, canary, and rollback so the runtime upgrade is
not one unreviewable change.

Disclosure: I maintain Rupture. The CLIs are MIT licensed:
https://github.com/ntoledo319/Rupture

## Guardrails

- Do not post on stale, unrelated, or already-solved threads.
- Do not lead with the product link.
- Include concrete commands or migration advice in every reply.
- Use one reply per thread; do not follow up unless someone asks.
- If a thread has a stricter self-promotion policy, follow that community rule.
