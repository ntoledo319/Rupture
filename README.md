# EOLkits — Migration Kits for AWS Platform Deprecations

> CLIs for the AWS deprecation deadlines that break production. Next up: **Amazon Linux 2 (Jun 30, 2026)**. Also: **Lambda Python 3.9/3.10/3.11** waves, and post-deadline cleanup for **Lambda Node.js 20**.

[![landing](https://img.shields.io/badge/landing-live-brightgreen)](https://eolkits.com)
[![tests](https://img.shields.io/badge/tests-126%20passing-brightgreen)](#tests)
[![license](https://img.shields.io/badge/license-MIT%20(open%20core)-blue)](#license)

AWS is killing runtimes on a hard schedule. When a deadline passes, deploys fail, functions get frozen, AMIs stop receiving patches. Most shops find out in production.

**EOLkits ships one CLI per deadline.** Each kit scans your accounts, rewrites the broken code, patches the IaC, generates a safe canary plan, and produces a rollback script. All kits work offline via fixtures so you can evaluate before you run them against AWS.

---

## The deadlines

| Kit | Deadline | What breaks | Status |
|---|---|---|---|
| [**al2023-gate**](./kits/al2023-gate) | **Jun 30, 2026** — Amazon Linux 2 EOL | `yum`, `amazon-linux-extras`, `ntpd`, `iptables`, Python 2 | **Live deadline** |
| [**python-pivot**](./kits/python-pivot) | **Lambda Python 3.9/3.10/3.11** EOL waves | `distutils`, `imp`, `collections.Mapping`, native wheels | Active |
| [**lambda-lifeline**](./kits/lambda-lifeline) | Apr 30, 2026 — Lambda Node.js 20 EOL (Phase 1, **passed**) | `require()`, `aws-sdk` v2, `URL` globals, OpenSSL 3 hashes | Post-deadline cleanup |

> Phase 1 for Node.js 20 ended Apr 30, 2026 — security patches stop. Phase 2 (Aug 31) blocks creating new functions on `nodejs20.x`; Phase 3 (Sep 30) blocks updating existing ones. If you're still on `nodejs20.x`, `lambda-lifeline` is the cleanup path before the Sep 30 cliff.

Every kit ships the same 6 pillars:

1. **scan** — enumerate affected resources across regions (fixture or live via boto3)
2. **codemod / remap** — rewrite source and config to the new runtime
3. **audit** — find the dependency landmines (native wheels, deprecated modules)
4. **iac** — patch SAM / CDK (Python+TS) / Terraform / Serverless / Packer / Ansible
5. **deploy** — staged canary (5 → 25 → 50 → 100) with CloudWatch alarm rollback
6. **rollback** — one command back to the previous version

---

## Install

Each kit is standalone. `al2023-gate` and `python-pivot` are Python CLIs; `lambda-lifeline` is a Node CLI. Clone and install the one you need.

For the live deadline (AL2 → AL2023, Jun 30):

```bash
git clone https://github.com/ntoledo319/EOLkits.git
cd EOLkits/kits/al2023-gate   # or kits/python-pivot
pip install -e .
al2023-gate --help
```

For Node 20 cleanup (before the Sep 30 Phase 3 cliff):

```bash
cd EOLkits/kits/lambda-lifeline
npm install
npm link
lambda-lifeline --help
```

The Python kits require Python 3.10+. Live mode uses `boto3`; fixture mode requires nothing.

---

## Hosted fulfillment on GRACE

The hosted EOLkits site now targets the GRACE deployment shape:

- `eolkits.com` is the existing static GRACE satellite.
- selected API paths on `eolkits.com` are reverse-proxied to the paid fulfillment API satellite.
- Uploads, report PDFs, idempotency, verification records, and jobs use the GRACE VPS filesystem + local SQLite state instead of Cloudflare KV/R2/Queues.

See [`deploy/grace/README.md`](./deploy/grace/README.md) for the exact no-duplicate wiring. Keep the existing `eolkits` static satellite; add only `eolkits-api` for paid API/webhook fulfillment.

---

## GitHub Action

Run the free PR check from GitHub Actions:

```yaml
- uses: ntoledo319/EOLkits@v1
  with:
    kit: auto
    path: .
    fail-on: high
    comment-pr: true
```

The action runs dry-run, path-safe checks from all three kits and can comment findings on pull requests.

---

## 30-second demo

Live deadline first — Amazon Linux 2 → AL2023:

```bash
# Scan what's about to break (offline, no AWS creds needed)
al2023-gate scan --fixture test/fixtures/inventory.json --format table

# Remap package names (yum → dnf, retired packages → replacements)
al2023-gate remap --packages packages.txt

# Patch cloud-init / launch-template / Packer / Ansible
al2023-gate cloudinit --path user-data.yaml --apply

# Generate the rollout runbook for EKS / ECS / Beanstalk / ASG
al2023-gate runbook --target eks
```

Same shape for `python-pivot` and `lambda-lifeline` — see each kit's README for the full walkthrough with captured output.

---

## Pricing

| SKU | Price | What you get | Delivery |
|---|---|---|---|
| **CLI (free)** | $0 | All three kits, MIT, no limits | `git clone` |
| **Audit PDF** | $299 (surge to $399 inside 30 days, $599 inside 7 days) | A hash-anchored, deterministic report scoring every finding by severity × blast-radius, with a roll-forward roadmap and cost-of-not-fixing estimate | Email within 5 minutes |
| **Migration Pack** | $1,499 | A real PR opened on your repo with codemods + IaC patches + canary plan + rollback. Refund auto-fires if CI fails | GitHub App opens PR within 5 minutes |
| **Org License** | $14,999 / yr | Live rule-pack feed, private rule extensions, unlimited runs, one-year validity | License key emailed |
| **Drift Watch** | $19 / mo | Weekly re-scan of a read-only IAM role; delta PDF on change; auto-PR on new deprecation | Cron-driven |

**[→ Pricing page](https://eolkits.com#pricing)**

---

## Why this exists

AWS publishes deprecation notices on a blog. Your deploys will fail on a Tuesday. The fix is usually not one-line — it's native wheels that don't exist for the new runtime, OpenSSL 3 hashes your code depended on, an IMDSv1 call that's now blocked, an `iptables` rule that no longer works on nftables.

EOLkits automates AWS migrations off deprecated runtimes — deterministically, safely, and before the deadline. It's opinionated, well-tested (126 tests across kits + apps), and safe — everything is dry-run by default, everything has a rollback path.

---

## Tests

```bash
# lambda-lifeline: 24 tests (Node, node --test)
cd kits/lambda-lifeline && npm test

# al2023-gate: 48 tests
cd kits/al2023-gate && pytest -q

# python-pivot: 44 tests
cd kits/python-pivot && pytest -q

# apps/runner: 7 tests
cd apps/runner && pytest -q

# apps/worker: 3 tests (vitest)
cd apps/worker && npm test
```

126 passing across kits + apps.

---

## Roadmap

Shipped:
- [x] al2023-gate — Amazon Linux 2 → AL2023 *(Jun 30, 2026 — live deadline)*
- [x] python-pivot — Lambda Python 3.9/3.10/3.11 → 3.12 *(rolling EOL waves)*
- [x] lambda-lifeline — Lambda Node.js 20 → 22 *(Phase 1 passed Apr 30; Phase 3 cliff Sep 30)*

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

- 🌐 [Landing page](https://eolkits.com)
- 🚀 [Show HN post](./launch/show-hn-final.md)
- 📝 [Blog post: Migrating Lambda Node.js 20 → 22](./launch/blog-post.md)
- 💬 [Direct support reply templates](./launch/thread-answers.md)
- 💬 Issues: use the repo tracker

---

*EOLkits migrates AWS workloads off deprecated runtimes — automatically, deterministically, and before the deadline.*
