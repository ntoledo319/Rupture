# Rupture — Migration Kits for AWS Platform Deprecations

> CLIs for the real AWS deprecation deadlines that break production: **Lambda Node.js 20**, **Amazon Linux 2**, **Lambda Python 3.9/3.10/3.11**.

[![landing](https://img.shields.io/badge/landing-live-brightgreen)](https://ntoledo319.github.io/Rupture)
[![tests](https://img.shields.io/badge/tests-116%20passing-brightgreen)](#tests)
[![license](https://img.shields.io/badge/license-MIT%20(open%20core)-blue)](#license)

AWS is killing runtimes on a hard schedule. When a deadline passes, deploys fail, functions get frozen, AMIs stop receiving patches. Most shops find out in production.

**Rupture ships one CLI per deadline.** Each kit scans your accounts, rewrites the broken code, patches the IaC, generates a safe canary plan, and produces a rollback script. All kits work offline via fixtures so you can evaluate before you run them against AWS.

---

## The deadlines

| Kit | Deadline | What breaks | Status |
|---|---|---|---|
| [**lambda-lifeline**](./kits/lambda-lifeline) | **Apr 30, 2026** — Lambda Node.js 20 EOL (Phase 1) | `require()`, `aws-sdk` v2, `URL` globals, OpenSSL 3 hashes | Ready |
| [**al2023-gate**](./kits/al2023-gate) | **Jun 30, 2026** — Amazon Linux 2 EOL | `yum`, `amazon-linux-extras`, `ntpd`, `iptables`, Python 2 | Ready |
| [**python-pivot**](./kits/python-pivot) | **Lambda Python 3.9/3.10/3.11** EOL waves | `distutils`, `imp`, `collections.Mapping`, native wheels | Ready |

Every kit ships the same 6 pillars:

1. **scan** — enumerate affected resources across regions (fixture or live via boto3)
2. **codemod / remap** — rewrite source and config to the new runtime
3. **audit** — find the dependency landmines (native wheels, deprecated modules)
4. **iac** — patch SAM / CDK (Python+TS) / Terraform / Serverless / Packer / Ansible
5. **deploy** — staged canary (5 → 25 → 50 → 100) with CloudWatch alarm rollback
6. **rollback** — one command back to the previous version

---

## Install

Each kit is standalone. `lambda-lifeline` is a Node CLI; `al2023-gate` and `python-pivot` are Python CLIs. Clone and install the one you need:

```bash
git clone https://github.com/ntoledo319/Rupture.git
cd Rupture/kits/lambda-lifeline
npm install
npm link
lambda-lifeline --help
```

For the Python kits:

```bash
cd Rupture/kits/al2023-gate   # or kits/python-pivot
pip install -e .
al2023-gate --help
```

The Python kits require Python 3.10+. Live mode uses `boto3`; fixture mode requires nothing.

---

## GitHub Action

Run the free PR check from GitHub Actions:

```yaml
- uses: ntoledo319/Rupture@v1
  with:
    kit: auto
    path: .
    fail-on: high
    comment-pr: true
```

The action runs dry-run, path-safe checks from all three kits and can comment findings on pull requests.

---

## 30-second demo

```bash
# Scan what's about to break (offline, no AWS creds needed)
lambda-lifeline scan --fixture test/fixtures/lambda-inventory.json --format table

# Rewrite source for Node.js 22
lambda-lifeline codemod ./src --apply

# Audit native-module dependencies
lambda-lifeline audit ./package.json

# Patch SAM/CDK/Terraform
lambda-lifeline iac ./template.yaml --apply

# Generate canary deploy plan
lambda-lifeline deploy plan --alias prod
```

See [kits/lambda-lifeline/README.md](./kits/lambda-lifeline) for the full walkthrough with captured output.

---

## Pricing

| SKU | Price | What you get | Delivery |
|---|---|---|---|
| **CLI (free)** | $0 | All three kits, MIT, no limits | `git clone` |
| **Audit PDF** | $299 (surge to $399 inside 30 days, $599 inside 7 days) | A hash-anchored, deterministic report scoring every finding by severity × blast-radius, with a roll-forward roadmap and cost-of-not-fixing estimate | Email within 5 minutes |
| **Migration Pack** | $1,499 | A real PR opened on your repo with codemods + IaC patches + canary plan + rollback. Refund auto-fires if CI fails | GitHub App opens PR within 5 minutes |
| **Org License** | $14,999 / yr | Live rule-pack feed, private rule extensions, unlimited runs, one-year validity | License key emailed |
| **Drift Watch** | $19 / mo | Weekly re-scan of a read-only IAM role; delta PDF on change; auto-PR on new deprecation | Cron-driven |

**[→ Pricing page](https://ntoledo319.github.io/Rupture#pricing)**

---

## Why this exists

AWS publishes deprecation notices on a blog. Your deploys will fail on a Tuesday. The fix is usually not one-line — it's native wheels that don't exist for the new runtime, OpenSSL 3 hashes your code depended on, an IMDSv1 call that's now blocked, an `iptables` rule that no longer works on nftables.

Rupture automates AWS migrations off deprecated runtimes — deterministically, safely, and before the deadline. It's opinionated, well-tested (116 tests across 3 kits), and safe — everything is dry-run by default, everything has a rollback path.

---

## Tests

```bash
# lambda-lifeline: 24 tests
cd kits/lambda-lifeline && pytest -q

# al2023-gate: 48 tests
cd kits/al2023-gate && pytest -q

# python-pivot: 44 tests
cd kits/python-pivot && pytest -q
```

116 passing across all kits.

---

## Roadmap

Shipped:
- [x] lambda-lifeline — Lambda Node.js 20 → 22
- [x] al2023-gate — Amazon Linux 2 → AL2023
- [x] python-pivot — Lambda Python 3.9/3.10/3.11 → 3.12

Queued:
- [ ] imds-v2-gate — IMDSv1 → IMDSv2 enforcement
- [ ] rds-pg-gate — RDS for PostgreSQL major version EOLs
- [ ] eks-version-gate — EKS control-plane version migrations

Each new kit is free forever for bundle customers.

---

## License

Open-core: the CLI code in this repo is MIT-licensed. The paid tiers include hash-anchored audit reports, automated PR bots, and rule-pack feeds.

---

## Links

- 🌐 [Landing page](https://ntoledo319.github.io/Rupture)
- 🚀 [Show HN draft](./launch/show-hn-draft.md)
- 📝 [Blog post: Migrating Lambda Node.js 20 → 22](./launch/blog-post.md)
- 💬 [Direct support reply templates](./launch/thread-answers.md)
- 💬 Issues: use the repo tracker

---

*Rupture migrates AWS workloads off deprecated runtimes — automatically, deterministically, and before the deadline.*
