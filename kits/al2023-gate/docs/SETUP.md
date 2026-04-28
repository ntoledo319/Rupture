# al2023-gate — 30-minute setup

From zero to "I have a tested AL2023 AMI building in my account."

## 0. Prereqs (5 min)

- Python 3.9+ (`python3 --version`)
- AWS credentials in your environment (profile or env vars) with read access to EC2, EKS, ECS, and Elastic Beanstalk
- Packer 1.9+ installed locally (`brew install packer` or <https://developer.hashicorp.com/packer/downloads>) — only needed if you'll run the build yourself

## 1. Install (2 min)

```bash
git clone https://github.com/ntoledo319/Rupture.git
cd Rupture/kits/al2023-gate
pip install -e .

# verify
al2023-gate --version
al2023-gate --help
```

With the AWS optional extras if you want live scanning:

```bash
pip install -e '.[aws]'
```

## 2. Scan your account (5 min)

```bash
# single region
al2023-gate scan --regions us-east-1 --format table

# multi-region, JSON for CI / reports
al2023-gate scan --regions us-east-1,us-east-2,eu-west-1 --format json --out findings.json

# just fail the build if anything AL2 shows up
al2023-gate scan --regions us-east-1 --strict
```

The scanner is 100 % read-only. You will see findings for EC2 instances, launch templates, EKS node groups, ECS task definitions (when task defs reference AMIs), and Elastic Beanstalk environments.

## 3. Build your package list (5 min)

From the findings, list the packages each AL2 AMI currently installs. If you don't know, SSH to a representative instance and run:

```bash
rpm -qa --queryformat '%{NAME}\n' | sort -u > packages.txt
```

Then remap:

```bash
al2023-gate remap --file packages.txt --format md > remap-report.md
```

Read `remap-report.md`. Items marked ⚠️ require your attention (removed packages, version bumps, paradigm shifts like `ntp → chrony`).

## 4. Generate your AL2023 Packer template (3 min)

```bash
al2023-gate packer --packages packages.txt --region us-east-1 --out ./build
cd build
packer init .
packer build al2023.pkr.hcl
```

The template is fully parameterized — edit `variable` blocks for subnet, KMS, AMI name prefix, etc.

## 5. Diff your cloud-init / user-data (3 min)

```bash
al2023-gate cloudinit path/to/user-data.sh
al2023-gate cloudinit path/to/cloud-init-dir/    # directory scan
al2023-gate cloudinit path/to/user-data.sh --strict    # for CI
```

11 rules. Fix anything `critical` or `high` before promoting the new AMI.

## 6. Patch your Ansible (3 min)

```bash
# dry-run first — ALWAYS
al2023-gate ansible roles/

# then apply
al2023-gate ansible roles/ --apply

# commit and review
git diff roles/
```

## 7. Pick your runbook and execute (4 min)

For each resource category, generate its runbook and execute:

```bash
al2023-gate runbook --kind asg        --name prod-api-asg --region us-east-1   --out docs/asg-migration.md
al2023-gate runbook --kind eks        --name prod         --cluster prod-eks    --out docs/eks-migration.md
al2023-gate runbook --kind ecs        --name payment      --cluster prod-ecs    --out docs/ecs-migration.md
al2023-gate runbook --kind beanstalk  --name analytics    --region eu-west-1    --out docs/eb-migration.md
```

Each runbook has:
- Pre-flight checklist (AMI tagged, staging soak ≥24 h, alarms in place)
- Execute steps with exact AWS CLI commands
- Rollback procedure

---

## CI integration

Drop this into `.github/workflows/al2023-gate.yml`:

```yaml
name: AL2023 readiness
on: [pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install al2023-gate
      - run: al2023-gate cloudinit user-data.sh --strict
      - run: al2023-gate ansible roles/ --strict
      - name: Live account scan
        env:
          AWS_REGION: us-east-1
          AWS_ACCESS_KEY_ID: ${{ secrets.READONLY_KEY }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.READONLY_SECRET }}
        run: al2023-gate scan --regions us-east-1 --strict
```

---

## Troubleshooting

**`boto3 not found`** — `pip install 'al2023-gate[aws]'`.

**Scanner finds nothing but I know I have AL2 instances** — your IAM role needs `ec2:DescribeInstances`, `ec2:DescribeImages`, `ec2:DescribeLaunchTemplateVersions`, `eks:ListClusters`, `eks:ListNodegroups`, `ecs:ListTaskDefinitions`, `ecs:DescribeTaskDefinition`, `elasticbeanstalk:DescribeEnvironments`.

**Packer build fails with "source AMI not found"** — AL2023 AMIs are owned by account `137112412989`. If you have an SCP blocking cross-account AMIs, whitelist that owner.

**Ansible patcher rewrote too much** — it defaults to dry-run. If you already ran with `--apply`, `git reset --hard` and re-run `--apply` with `--strict` which fails on ambiguous cases.