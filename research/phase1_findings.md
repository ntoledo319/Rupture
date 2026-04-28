# Phase 1 — Rupture Scan Findings

**Scan date:** 2026-04-28
**Deadline window:** 2026-05-05 → 2026-07-27 (adjusted to include phased deprecations with hard blocks in window)
**Sources consulted:** AWS official docs, AWS re:Post, CloudQuery blog, HeroDevs blog, GitHub issues (awslabs, remotion, GSA, renovate), endoflife.date, Amazon Linux 2 FAQ

---

## Candidate A — AWS Lambda Node.js 20.x EOL ⭐ RECOMMENDED

| Field | Value |
|---|---|
| **Primary source** | https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html |
| **Secondary source** | https://nodejs.org/en/about/previous-releases (Node.js upstream EOL) |
| **Phase 1 deadline** | **April 30, 2026 (2 days out)** — security patches stop |
| **Phase 2 deadline** | **August 31, 2026 (125 days out)** — block function create |
| **Phase 3 deadline** | **September 30, 2026 (155 days out)** — block function update (HARD) |
| **Affected stack** | AWS Lambda + Node.js 20 + TypeScript/JS ecosystem |
| **Also affects** | nodejs18.x (already past), nodejs16.x, Lambda Layers with native modules |
| **Public pain signals** | • AWS Health Dashboard emails going out now<br>• github.com/awslabs/landing-zone-accelerator-on-aws/issues/996 (official AWS repo)<br>• github.com/awslabs/landing-zone-accelerator-on-aws/issues/961<br>• github.com/remotion-dev/remotion/issues/6108<br>• github.com/GSA/data.gov/issues/5578 (US federal gov affected)<br>• github.com/renovatebot/renovate/discussions/21586<br>• github.com/nodejs/userland-migrations/issues/180 |
| **Community size** | Every team running Node on AWS Lambda — 7-figure function count globally |
| **Existing solutions** | • CloudQuery: detection only (enterprise SaaS)<br>• HeroDevs: paid post-EOL support (enterprise $$$$)<br>• aws-samples/lambda-runtime-update-helper: batch-runtime-flip only, NO code migration, NO tests, unmaintained<br>• **GAP:** No integrated scan → code-fix → test → staged deploy kit at SMB price |
| **Breaking-change surface** | • Import assertions (`assert`→`with`) — codemod-able<br>• Native module ABI (sharp, bcrypt, better-sqlite3) — `npm rebuild`<br>• CA certs (`NODE_EXTRA_CA_CERTS`) — config fix<br>• Buffer API negative indices — detectable<br>• Streams high water mark 16KB→64KB — perf risk flag |
| **Recommended kit format** | Migration Script Kit: (1) multi-account/region scanner (CLI), (2) codemod for `assert`→`with`, (3) package.json dep audit (native binaries), (4) CA cert auto-fix, (5) SAM/CDK/Terraform IaC patcher, (6) staged canary deploy script, (7) rollback script, (8) CI template |
| **Build complexity** | **Medium** — all pieces are well-defined, each ~2-4 hours; heavy lifting in testing |
| **Build time estimate** | 8-14 hours of VM work for MVP |
| **Urgency score** | **10/10** |
| **Why this wins** | Imminent deadline (2 days!) = panic buyers; widespread stack; pain is concrete and codified in official AWS docs; no integrated SMB-priced solution; buyers are senior engineers with budget authority; recurring revenue angle (nodejs22→24 migration in 2027) |

---

## Candidate B — Amazon Linux 2 EOL

| Field | Value |
|---|---|
| **Primary source** | https://aws.amazon.com/amazon-linux-2/faqs/ (Q: "When will support for Amazon Linux 2 end?" A: "2026-06-30") |
| **Deadline** | **June 30, 2026 (63 days out)** |
| **Affected stack** | EC2, ECS (AL2 AMIs), EKS nodes, on-prem AL2 VMs, Elastic Beanstalk AL2 platforms |
| **Public pain signals** | • AWS re:Post: "Amazon 2023 - A real disaster" — DNF broken, Python chaos, restricted mirror access<br>• r/aws: "Migrating from AL2 to AL2023" thread<br>• r/aws: "Amazon Linux 2025" thread<br>• tuxcare.com EOL guide (vendor content = active buyer search)<br>• CIQ blog on AL2023 vs Enterprise Linux alternatives<br>• Wojciech Lepczyński blog, DjaoDjin blog, Medium (EKS migration) |
| **Community size** | Millions of EC2 instances; every long-lived AWS workload touches this |
| **Existing solutions** | • AWS official "prepare-for-al2023.html" docs (prose only)<br>• CIQ and TuxCare sell **extended support subscriptions** (not migration automation)<br>• **GAP:** No opinionated "scan your AMI + Packer template + Ansible playbook + replace" kit |
| **Breaking-change surface** | • no `amazon-linux-extras`, DNF instead of YUM<br>• Python 2 removed, Python 3.9 default<br>• No in-place upgrade — must rebuild AMI<br>• SELinux default on<br>• cloud-init differences<br>• Package name changes (openssl, etc.) |
| **Recommended kit format** | Infrastructure Template: (1) AMI scanner (which AMIs are AL2), (2) Packer template for AL2023 equivalent, (3) dependency mapping (AL2 pkg → AL2023 pkg), (4) Ansible playbook patches, (5) cloud-init diff tool, (6) ECS/EKS AMI swap runbook |
| **Build complexity** | **Medium-High** — requires real EC2 testing, AMI build pipeline |
| **Build time estimate** | 14-24 hours VM + external test infra needed (can use AWS free tier with user's creds, but adds Checkpoint complexity) |
| **Urgency score** | **8/10** |
| **Why it could win** | Bigger blast radius than Lambda; longer runway = more buyers who haven't started yet; enterprise procurement-friendly (Packer/Ansible = ops-team language) |
| **Why it loses vs A** | Needs real AWS account to test AMI builds (user would need to provide creds OR we skip real testing and just ship Packer templates + docs — lower-quality kit); longer build cycle eats launch urgency |

---

## Candidate C — AWS Lambda Python 3.10 EOL

| Field | Value |
|---|---|
| **Primary source** | https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html |
| **Deadline** | **October 31, 2026 (186 days out — OUTSIDE STRICT 7-90 WINDOW but Phase 2 block-create = Nov 30, 2026)** |
| **Also bundled** | Python 3.9 already deprecated (Dec 15 2025); Python 3.11 EOL Jun 30 2027 |
| **Affected stack** | Lambda + Python (largest Lambda language by function count) |
| **Public pain signals** | Moderate — less urgent than Node.js because Python 3.10 still has ~6 months |
| **Existing solutions** | pyupgrade, ruff, 2to3 (general-purpose); no Lambda-specific Python migration kit |
| **Build complexity** | Medium (similar to A but in Python) |
| **Urgency score** | **6/10** — too far out for "panic buy" dynamic, but could be a V2 kit |
| **Verdict** | **Skip for Phase 1 launch**; keep as a V2 product to extend the franchise |

---

## Ranking

1. 🏆 **Candidate A — Lambda Node.js 20 EOL Migration Kit** (urgency 10/10, competitive gap, recurring franchise)
2. **Candidate B — Amazon Linux 2 → AL2023 Migration Kit** (urgency 8/10, bigger TAM, higher build cost)
3. **Candidate C — Lambda Python 3.10 → 3.12 Migration Kit** (urgency 6/10, reserve for V2)

## Recommendation: Ship Kit A. Reserve Kit B and Kit C as the product roadmap (the "Rupture Kits" brand has legs — every runtime EOL is a paid kit).