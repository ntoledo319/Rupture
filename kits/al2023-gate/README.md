# al2023-gate
### Amazon Linux 2 → AL2023 migration kit — scan, remap, patch, ship, rollback

> **Deadline: 2026-06-30.** Amazon Linux 2 standard support ends. No new updates. No new patches. Critical CVEs become your problem. AWS will not extend again — the date has already been pushed twice.

`al2023-gate` is a single-binary, dependency-light Python tool that finds every AL2-based compute resource in your AWS account, generates the Packer template + Ansible patches + cloud-init diffs to rebuild them on AL2023, and produces resource-type-specific migration runbooks you can actually execute.

Works offline (fixture mode) for demos, audits, or air-gapped reviews. Works live against AWS with standard boto3 credentials.

[![Tests](https://img.shields.io/badge/tests-48%20passing-green)](test/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![AL2 EOL](https://img.shields.io/badge/AL2%20EOL-2026--06--30-red)](https://aws.amazon.com/amazon-linux-2/faqs/)

---

## The deadline

| Milestone | Date | What breaks |
|---|---|---|
| **Standard support ends** | **2026-06-30** | No patches, no security updates, no CVE backports |
| Maintenance support ends | 2027-06-30 | Full EOL. Instance launches from AL2 AMIs start failing. |
| New AL2 AMI publications | Stopped | Already happening for most AWS-official AL2 AMIs |

**63 days out** as of this release. If you have production EC2, EKS, ECS, or Elastic Beanstalk resources on AL2, you need a migration plan today.

Primary source: <https://aws.amazon.com/amazon-linux-2/faqs/>

---

## Install

```bash
pip install al2023-gate               # from PyPI (coming soon)
# or run from source:
git clone https://github.com/ntoledo319/Rupture.git
cd Rupture/kits/al2023-gate
pip install -e .
```

No external runtime deps. `boto3` is optional — only required for `scan` against live AWS. All other commands work offline.

---

## The 6 commands

```
al2023-gate scan        # find all AL2 resources across EC2, LT, EKS, ECS, EB
al2023-gate remap       # translate yum packages → dnf equivalents (curated table of ~50)
al2023-gate packer      # generate ready-to-build Packer HCL for your AL2023 AMI
al2023-gate cloudinit   # diff user-data / cloud-init scripts for known AL2023 breakage
al2023-gate ansible     # rewrite ansible playbooks (yum→dnf, python2→3, extras removal)
al2023-gate runbook     # emit a resource-specific migration playbook (ASG / EKS / ECS / EB)
```

Each one does exactly one thing, can be piped, and has a `--format json` mode for CI use.

---

## 5-minute demo

### 1. Scan

```bash
$ al2023-gate scan --fixture test/fixtures/inventory.json

▸ Scanning fixture test/fixtures/inventory.json
ℹ Scanned 6 resource(s). 4 AL2, 0 AL1

Type                    Id                                    Region      Platform  Severity
--------------------------------------------------------------------------------------------
ec2_instance            i-0a1b2c3d4e5f60718                   us-east-1   al2       high
launch_template         lt-0f1e2d3c4b5a60978                  us-east-1   al2       high
eks_nodegroup           prod-cluster/ng-web-2a                us-east-2   al2       high
ecs_task_definition     payment-worker:47                     us-east-1   other     ok
beanstalk_environment   analytics-prod-env                    eu-west-1   al2       high
ec2_instance            i-0ffffeeeeddddccbb                   us-east-1   al2023    ok

⚠ AL2 EOL in 63 day(s). Next: `al2023-gate packer` to scaffold an AL2023 AMI build.
```

Add `--strict` for CI (exits 1 if any AL2 resources are found). Add `--format json|csv|md` for machine output. Live AWS: drop `--fixture` and add `--regions us-east-1,eu-west-1`.

### 2. Remap your `yum` package list

```bash
$ al2023-gate remap docker nginx1 python3.8 php7.4 ntp yum-utils

AL2 PACKAGE  AL2023 EQUIVALENT  CATEGORY       NOTE
---------------------------------------------------
docker       docker             extras_to_dnf ! AL2 used `amazon-linux-extras install docker`. AL2023: `dnf install docker`.
nginx1       nginx              renamed         AL2 extras `nginx1` → AL2023 `nginx` (mainline).
python3.8    python3.11         replaced_by   ! AL2023 default python is 3.11. 3.8 not available.
php7.4       php8.2             replaced_by   ! PHP 7.4 is upstream EOL. AL2023 has php8.2 only.
ntp          chrony             replaced_by   ! ntpd is removed. AL2023 uses chrony for time sync.
yum-utils    dnf-utils          renamed         DNF replaces YUM. `yum-config-manager` is now `dnf config-manager`.
```

A `!` marks packages that require action — the rest are drop-in. Feed a file with `--file packages.txt`.

### 3. Generate a Packer template

```bash
$ al2023-gate packer --packages packages.txt --out ./build

▸ Packer template generator · ./build
ℹ Input packages: 23
✓ wrote build/al2023.pkr.hcl
✓ wrote build/migration-report.md
ℹ Next: `cd build && packer init . && packer build al2023.pkr.hcl`
```

Produces:
- `al2023.pkr.hcl` — a fully-parameterized Packer template (AWS amazon-ebs builder, AL2023 source AMI filter, pre-baked provisioners for `dnf update`, chrony enable, SSH hardening, cloud-init clean)
- `migration-report.md` — per-package action items grouped by category (removed, replaced, renamed) with AWS doc links

### 4. Diff your cloud-init / user-data

```bash
$ al2023-gate cloudinit user-data.sh

test/fixtures/user-data.sh
  [medium]   line 5  yum-to-dnf           yum update -y
  [critical] line 6  amazon-linux-extras  amazon-linux-extras install nginx1 -y
  [critical] line 15 python2-shebang      #!/usr/bin/python
  [high]     line 10 ntp-service          systemctl enable ntpd
  [high]     line 21 iptables-service     systemctl enable iptables
```

11 rules built in. Cloud-init is not auto-rewritten — too sensitive. You get precise line numbers + suggested edits instead.

### 5. Patch Ansible playbooks

```bash
$ al2023-gate ansible roles/ --apply

▸ Ansible patcher · roles/ · APPLY
ℹ [rewrite] roles/web/tasks/main.yml · yum module → dnf module · 3 hit(s)
ℹ [rewrite] roles/web/tasks/main.yml · yum task → dnf task (top-level) · 1 hit(s)
ℹ [lint]    roles/web/tasks/main.yml:42 · ntpd is not on AL2023 by default. Use chrony.
ℹ [lint]    roles/security/tasks/selinux.yml:3 · SELinux default changed; verify policy.

✓ 4 file(s), 11 edit(s) applied.
```

Safe, narrow rewrites only. Anything ambiguous is flagged for human review, not auto-changed. Default is dry-run.

### 6. Get a resource-specific runbook

```bash
$ al2023-gate runbook --kind asg --name prod-api-asg --region us-east-1 --out RUNBOOK.md
✓ wrote RUNBOOK.md
```

Produces a checklist with:
- Pre-flight: AMI tagged, staging soak ≥24h, alarms in place
- Execute: exact `aws` CLI commands for `create-launch-template-version` + `instance-refresh` with canary warm-up
- Rollback: previous Launch Template version swap + terminate-replacement

Same command supports `--kind eks|ecs|beanstalk` — each with resource-appropriate steps.

---

## What's in the box

| Component | Purpose |
|---|---|
| **Scanner** | Multi-region, multi-resource discovery. Classifies AMIs via AL2 vs AL2023 vs AL1 pattern matching. |
| **Remap table** | ~50 curated AL2→AL2023 package entries (docker, nginx, php, postgresql, python, openssl ABI, curl→curl-minimal, ntp→chrony, yum→dnf, …). Handles `extras_to_dnf`, `renamed`, `replaced_by`, `removed`. |
| **Packer generator** | Full AWS amazon-ebs builder template with chrony, SSH hardening, cloud-init reset, dnf update, and your curated package list. |
| **cloud-init differ** | 11 rules for the highest-frequency AL2 user-data patterns that break on AL2023. |
| **Ansible patcher** | yum→dnf (module & top-level), `amazon-linux-extras` task removal, python2→3 path rewrites, SELinux/ntp/iptables lint. |
| **Runbook generator** | ASG (instance refresh + rollback), EKS (blue/green node group), ECS (task def base image swap), Beanstalk (CNAME swap). |
| **48-test suite** | Every command, every format, every exit-code path. All offline. |

---

## Safety

- Every write operation defaults to **dry-run**. `--apply` is required to touch a file.
- `scan` is strictly read-only (boto3 `Describe*` / `List*` only).
- Rollback is built into every runbook and tested.
- No telemetry. No network calls outside AWS. No LLM.

---

## Free vs paid

| | Free (this repo) | Team ($999) | Enterprise ($2,499) |
|---|---|---|---|
| Scanner | ✓ | ✓ | ✓ |
| Remap table (~50 pkgs) | ✓ | ✓ | ✓ |
| Packer generator | ✓ | ✓ | ✓ |
| cloud-init differ | ✓ | ✓ | ✓ |
| Ansible patcher | ✓ | ✓ | ✓ |
| 4 runbooks (ASG/EKS/ECS/EB) | ✓ | ✓ | ✓ |
| PDF migration playbook (printable) | — | ✓ | ✓ |
| 2-hour captioned video walkthrough | — | ✓ | ✓ |
| Expanded remap table (200+ pkgs, EE repos, Wavefront, Datadog, New Relic agents) | — | ✓ | ✓ |
| Custom remap entries for your stack | — | 3 | Unlimited |
| Priority Slack channel | — | ✓ (7 days) | ✓ (30 days) |
| Live migration pairing session | — | — | 2 × 90 min |
| On-call during cutover window | — | — | ✓ |

Bundle with `lambda-lifeline` + `python-pivot`: see <https://rupture-kits.com>.

---

## Roadmap

- [ ] Live AWS Config Rules export (find AL2 at org-scale)
- [ ] Terraform state scanner (detect `ami-xxx` references without an API call)
- [ ] EKS AMI type auto-swap PR generator
- [ ] Datadog / New Relic agent migration shims
- [ ] GitHub Action template (`.github/workflows/al2023-gate-ci.yml`)

---

## License

MIT. See [LICENSE](LICENSE).

---

## Primary sources

- [AWS Amazon Linux 2 FAQ — EOL dates](https://aws.amazon.com/amazon-linux-2/faqs/)
- [AL2023 Comparison — packages, features, defaults](https://docs.aws.amazon.com/linux/al2023/ug/compare-with-al2.html)
- [EKS AMI types & release lifecycle](https://docs.aws.amazon.com/eks/latest/userguide/eks-optimized-amis.html)
- [Elastic Beanstalk platform deprecation schedule](https://docs.aws.amazon.com/elasticbeanstalk/latest/platforms/platforms-supported.html)

*Built by [Rupture Kits](https://github.com/ntoledo319/Rupture). Every AWS deprecation deadline deserves a kit.*