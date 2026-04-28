"""
Runbook generator: emits a step-by-step executable migration checklist tailored
to the resource type (EC2 ASG, EKS node group, ECS task, Beanstalk env).
"""
from __future__ import annotations
import argparse
from pathlib import Path
from . import util


RUNBOOKS = {
    "asg": """# EC2 Auto Scaling Group — AL2 → AL2023 swap

Target: ASG `{name}` in `{region}`.
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
   aws ec2 create-launch-template-version \\
     --launch-template-id $LT_ID \\
     --version-description "AL2023 migration" \\
     --source-version $(aws ec2 describe-launch-template-versions \\
       --launch-template-id $LT_ID --versions '$Latest' \\
       --query 'LaunchTemplateVersions[0].VersionNumber' --output text) \\
     --launch-template-data '{{"ImageId":"ami-xxxxxxxx"}}'
   ```
2. Update ASG to use `$Latest`:
   ```bash
   aws autoscaling update-auto-scaling-group \\
     --auto-scaling-group-name {name} \\
     --launch-template "LaunchTemplateId=$LT_ID,Version=\\$Latest"
   ```
3. Start instance refresh with canary warm-up:
   ```bash
   aws autoscaling start-instance-refresh \\
     --auto-scaling-group-name {name} \\
     --strategy Rolling \\
     --preferences '{{"MinHealthyPercentage":90,"InstanceWarmup":300,"CheckpointPercentages":[25,50,75,100],"CheckpointDelay":600}}'
   ```
4. Watch CloudWatch alarms + ASG event log for 60 min.

## Rollback
```bash
aws autoscaling start-instance-refresh --auto-scaling-group-name {name} --preferences '{{"MinHealthyPercentage":90}}'
# with LT version rolled back first:
aws autoscaling update-auto-scaling-group --auto-scaling-group-name {name} \\
  --launch-template "LaunchTemplateId=$LT_ID,Version=<previous-version>"
```
""",

    "eks": """# EKS managed node group — AL2 → AL2023

Target: Cluster `{cluster}` · NodeGroup `{name}` · Region `{region}`.
Approach: blue/green node group (safer than in-place amiType swap).

## Pre-flight
- [ ] EKS cluster version ≥ 1.29 (AL2023 supported 1.29+)
- [ ] Workloads have PodDisruptionBudgets set
- [ ] Relevant Helm charts / node-local DaemonSets tested on AL2023 kernel 6.1+
- [ ] IAM node role has permissions for AL2023 (same as AL2)

## Execute
1. Create new NG with `amiType=AL2023_x86_64_STANDARD` (or `AL2023_ARM_64_STANDARD`):
   ```bash
   aws eks create-nodegroup \\
     --cluster-name {cluster} --nodegroup-name {name}-al2023 \\
     --ami-type AL2023_x86_64_STANDARD \\
     --subnets subnet-xxx subnet-yyy \\
     --scaling-config minSize=2,maxSize=10,desiredSize=2 \\
     --instance-types m5.large \\
     --node-role arn:aws:iam::$ACCOUNT:role/EksNodeRole
   ```
2. Wait for new NG `ACTIVE`.
3. Cordon + drain old NG:
   ```bash
   for node in $(kubectl get nodes -l eks.amazonaws.com/nodegroup={name} -o name); do
     kubectl cordon $node
     kubectl drain $node --ignore-daemonsets --delete-emptydir-data --timeout=10m
   done
   ```
4. Verify all pods rescheduled to new NG.
5. Delete old NG:
   ```bash
   aws eks delete-nodegroup --cluster-name {cluster} --nodegroup-name {name}
   ```

## Rollback
Keep old NG until AL2023 NG is stable for ≥7 days. To roll back, scale old NG
back up and drain the new NG.
""",

    "ecs": """# ECS — task container base image AL2 → AL2023

Target: Task definition family `{name}` · Region `{region}`.
Approach: update container base image, publish new task def revision, rolling deploy.

## Pre-flight
- [ ] Dockerfile base image FROM line identified
- [ ] CI/CD build pipeline ready to rebuild image
- [ ] Deploy controller = CODE_DEPLOY or ECS (rolling)

## Execute
1. Update base image:
   ```dockerfile
   # Before: FROM amazonlinux:2
   # After:
   FROM public.ecr.aws/amazonlinux/amazonlinux:2023
   ```
2. Adjust package installs (see `al2023-gate remap --packages packages.txt`).
3. Rebuild & push image:
   ```bash
   docker build -t $REPO:al2023 .
   docker push $REPO:al2023
   ```
4. Register new task definition revision pointing at new image tag.
5. Update ECS service with `--force-new-deployment` and minimumHealthyPercent=100.

## Rollback
Update service back to previous task definition revision.
""",

    "beanstalk": """# Elastic Beanstalk — AL2 → AL2023 platform swap

Target: Environment `{name}` · Region `{region}`.
Approach: blue/green environment swap (safest). In-place platform update is also supported but can take 30+ min per instance.

## Pre-flight
- [ ] Target AL2023-based EB platform identified (e.g. "Python 3.11 running on 64bit Amazon Linux 2023")
- [ ] `.platform/` hooks reviewed for AL2-specific commands
- [ ] `.ebextensions/` reviewed for amazon-linux-extras / yum-specific config
- [ ] CNAME swap tested in staging

## Execute
1. Clone environment with new platform:
   ```bash
   aws elasticbeanstalk create-environment \\
     --application-name $APP --environment-name {name}-al2023 \\
     --platform-arn "arn:aws:elasticbeanstalk:{region}::platform/Python 3.11 running on 64bit Amazon Linux 2023/4.0.0" \\
     --version-label $VERSION
   ```
2. Wait for `Health=Green`, run smoke tests.
3. Swap CNAMEs:
   ```bash
   aws elasticbeanstalk swap-environment-cnames \\
     --source-environment-name {name} \\
     --destination-environment-name {name}-al2023
   ```
4. Monitor for 60 min, then terminate old environment.

## Rollback
Swap CNAMEs back. Keep old env running for ≥72h as insurance.
""",
}


def run(args: argparse.Namespace) -> int:
    target = args.kind
    if target not in RUNBOOKS:
        util.err(f"Unknown runbook kind: {target}. Choose one of: {', '.join(RUNBOOKS.keys())}")
        return 2
    content = RUNBOOKS[target].format(
        name=args.name or "<NAME>",
        region=args.region or "<REGION>",
        cluster=args.cluster or "<CLUSTER>",
    )
    if args.out:
        Path(args.out).write_text(content)
        util.ok(f"wrote {args.out}")
    else:
        print(content)
    return 0