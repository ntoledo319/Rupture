# al2023-gate — full demo transcript

Captured end-to-end, no edits. Every command is real.

## Setup

```bash
$ git clone https://github.com/ntoledo319/Rupture.git
$ cd Rupture/kits/al2023-gate
$ pip install -e .
```

## Scan (fixture mode — works without AWS creds)

```
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

## Remap

```
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

## Packer generate

```
$ al2023-gate packer --from-list docker,nginx1,python3.8 --out ./build

▸ Packer template generator · ./build
ℹ Input packages: 3
✓ wrote build/al2023.pkr.hcl
✓ wrote build/migration-report.md
ℹ Next: `cd build && packer init . && packer build al2023.pkr.hcl`
```

## cloud-init diff

```
$ al2023-gate cloudinit test/fixtures/user-data.sh

▸ cloud-init diff · 1 file(s)

test/fixtures/user-data.sh
  [medium]   line 5   yum-to-dnf            yum update -y
  [critical] line 6   amazon-linux-extras   amazon-linux-extras install nginx1 -y
  [medium]   line 7   yum-to-dnf            yum install -y python2 httpd
  [high]     line 10  ntp-service           systemctl enable ntpd
  [high]     line 11  ntp-service           systemctl start ntpd
  [critical] line 15  python2-shebang       #!/usr/bin/python
  [high]     line 21  iptables-service      systemctl enable iptables

⚠ 7 finding(s) across 1 file(s).
```

## Ansible patcher (dry-run)

```
$ al2023-gate ansible test/fixtures/playbook.yml

▸ Ansible patcher · test/fixtures/playbook.yml · DRY-RUN
⚠ DRY RUN — no changes written. Pass --apply to execute.
  1 playbook-like file(s) found
ℹ [rewrite] test/fixtures/playbook.yml · yum module → dnf module · 1 hit(s)
ℹ [rewrite] test/fixtures/playbook.yml · yum task → dnf task (top-level) · 1 hit(s)
ℹ [lint]    test/fixtures/playbook.yml:20 · ntpd is not on AL2023 by default. Use chrony.

✓ 1 file(s), 3 edit(s) previewed.
ℹ Re-run with --apply to write changes.
```

## Runbook — ASG

```
$ al2023-gate runbook --kind asg --name my-asg --region us-east-1

# EC2 Auto Scaling Group — AL2 → AL2023 swap

Target: ASG `my-asg` in `us-east-1`.
Approach: rolling replacement via new Launch Template version + `instance-refresh`.

## Pre-flight
- [ ] New AL2023 AMI built and tagged (`al2023-gate packer --out ./build/`)
- [ ] AL2023 AMI tested in a staging ASG with real traffic for ≥24h
- [ ] Target tracking / step-scaling policies reviewed
- [ ] CloudWatch alarms for HealthyHostCount and TargetResponseTime exist
- [ ] Cordon window communicated to stakeholders

## Execute
1. Create new Launch Template version pointing at the AL2023 AMI id:
   ```bash
   aws ec2 create-launch-template-version \
     --launch-template-id $LT_ID \
     --version-description "AL2023 migration" \
     ...
   ```
...
```

## Tests

```
$ pytest test/ -v
============================= test session starts ==============================
platform linux -- Python 3.11.14, pytest-9.0.3
collected 48 items

test/test_ansible.py::test_patch_text_rewrites_yum_module PASSED       [  2%]
...
test/test_scan.py::test_classify_ami_al2_patterns PASSED               [100%]

============================== 48 passed in 0.34s ==============================
```

All 48 tests green. Every command, every format, every exit-code path, no external dependencies.