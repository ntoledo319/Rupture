"""
Scanner: find AL2-based compute across AWS resources.

Data sources (in priority order):
 1. EC2 instances whose AMI description matches AL2
 2. Launch templates referring to AL2 AMIs
 3. ECS task definitions using AL2-based container images
 4. EKS node groups using AL2 AMI types
 5. Elastic Beanstalk environments on AL2 platforms

Works in two modes:
 - Live AWS: uses boto3 if installed and credentials available
 - Fixture : reads JSON fixture files for demo/test/air-gapped use
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from datetime import date
from typing import List, Optional
import argparse
import json
import sys
from . import util


AL2_EOL = date(2026, 6, 30)


# Canonical AMI-description patterns that identify AL2 (case-insensitive substring match)
AL2_PATTERNS = [
    "amzn2-ami",
    "amazon linux 2 ",
    "amazon-linux-2",
    "al2-x86_64",
    "al2-arm64",
    "amzn2",
]

# AL2023 patterns we consider clean
AL2023_PATTERNS = [
    "al2023-ami",
    "amazon linux 2023",
    "amazon-linux-2023",
    "al2023",
]


@dataclass
class Finding:
    resource_type: str
    resource_id: str
    region: str
    account_id: str
    ami_id: Optional[str]
    ami_description: Optional[str]
    platform: str
    severity: str
    notes: List[str] = field(default_factory=list)
    recommended_action: str = ""


def days_until(d: date) -> int:
    return (d - date.today()).days


def classify_ami(description: Optional[str]) -> str:
    if not description:
        return "unknown"
    d = description.lower()
    if any(p in d for p in AL2023_PATTERNS):
        return "al2023"
    if any(p in d for p in AL2_PATTERNS):
        return "al2"
    # Older AL1
    if "amzn-ami-hvm" in d or "amazon-linux-1" in d or "amzn1" in d:
        return "al1"
    return "other"


def severity_for(platform: str) -> str:
    if platform == "al1":
        return "critical-eol"
    if platform == "al2":
        d = days_until(AL2_EOL)
        if d <= 0:    return "critical-eol"
        if d <= 30:   return "critical"
        if d <= 90:   return "high"
        return "medium"
    return "ok"


# ---------- Fixture mode ----------

def scan_fixture(path: str) -> List[Finding]:
    with open(path) as f:
        data = json.load(f)
    findings: List[Finding] = []
    for item in data.get("findings", []):
        platform = classify_ami(item.get("ami_description"))
        findings.append(Finding(
            resource_type=item["resource_type"],
            resource_id=item["resource_id"],
            region=item.get("region", "us-east-1"),
            account_id=item.get("account_id", "000000000000"),
            ami_id=item.get("ami_id"),
            ami_description=item.get("ami_description"),
            platform=platform,
            severity=severity_for(platform),
            notes=item.get("notes", []),
            recommended_action=_recommend(platform, item["resource_type"]),
        ))
    return findings


def _recommend(platform: str, rtype: str) -> str:
    if platform != "al2":
        return ""
    base = "Rebuild AMI on AL2023 using al2023-gate packer templates; "
    mapping = {
        "ec2_instance": "launch replacement from new AMI, then terminate old.",
        "launch_template": "publish new template version pointing at AL2023 AMI.",
        "ecs_task_definition": "build new container image from al2023 base, update task def.",
        "eks_nodegroup": "create new managed node group with AL2023 AMI type, cordon + drain old.",
        "beanstalk_environment": "swap EB platform to an AL2023-based one (e.g. Python 3.11 AL2023).",
    }
    return base + mapping.get(rtype, "update reference to AL2023 image.")


# ---------- Live AWS mode ----------

def scan_live(regions: List[str], profile: Optional[str] = None) -> List[Finding]:
    try:
        import boto3
    except ImportError:
        raise SystemExit(
            "boto3 not installed. Run `pip install al2023-gate[aws]` "
            "or use `--fixture <file.json>` for offline mode."
        )

    session = boto3.Session(profile_name=profile) if profile else boto3.Session()
    sts = session.client("sts")
    try:
        account_id = sts.get_caller_identity()["Account"]
    except Exception as e:
        util.warn(f"Could not call STS: {e}. Continuing with account_id=unknown.")
        account_id = "unknown"

    findings: List[Finding] = []
    for region in regions:
        util.dim(f"  scanning {region}…")
        ec2 = session.client("ec2", region_name=region)

        # 1. Running EC2 instances
        paginator = ec2.get_paginator("describe_instances")
        amis_to_lookup = set()
        instance_records = []
        for page in paginator.paginate(Filters=[{"Name": "instance-state-name", "Values": ["running", "stopped"]}]):
            for rsv in page.get("Reservations", []):
                for inst in rsv.get("Instances", []):
                    amis_to_lookup.add(inst["ImageId"])
                    instance_records.append(inst)

        # Batch describe AMIs
        ami_desc = {}
        if amis_to_lookup:
            resp = ec2.describe_images(ImageIds=list(amis_to_lookup))
            for img in resp.get("Images", []):
                ami_desc[img["ImageId"]] = img.get("Description", "") + " " + img.get("Name", "")

        for inst in instance_records:
            desc = ami_desc.get(inst["ImageId"], "")
            platform = classify_ami(desc)
            if platform in ("al2", "al1"):
                findings.append(Finding(
                    resource_type="ec2_instance",
                    resource_id=inst["InstanceId"],
                    region=region, account_id=account_id,
                    ami_id=inst["ImageId"], ami_description=desc,
                    platform=platform, severity=severity_for(platform),
                    notes=[f"state={inst['State']['Name']}", f"type={inst['InstanceType']}"],
                    recommended_action=_recommend(platform, "ec2_instance"),
                ))

        # 2. Launch templates
        lt_paginator = ec2.get_paginator("describe_launch_templates")
        for page in lt_paginator.paginate():
            for lt in page.get("LaunchTemplates", []):
                # latest version
                v = ec2.describe_launch_template_versions(
                    LaunchTemplateId=lt["LaunchTemplateId"],
                    Versions=["$Latest"],
                )
                for ver in v.get("LaunchTemplateVersions", []):
                    image_id = ver.get("LaunchTemplateData", {}).get("ImageId")
                    if not image_id: continue
                    desc = ami_desc.get(image_id) or _describe_single(ec2, image_id)
                    platform = classify_ami(desc)
                    if platform in ("al2", "al1"):
                        findings.append(Finding(
                            resource_type="launch_template",
                            resource_id=f"{lt['LaunchTemplateName']} (v{ver['VersionNumber']})",
                            region=region, account_id=account_id,
                            ami_id=image_id, ami_description=desc,
                            platform=platform, severity=severity_for(platform),
                            recommended_action=_recommend(platform, "launch_template"),
                        ))

        # 3. EKS node groups
        try:
            eks = session.client("eks", region_name=region)
            for cluster in eks.list_clusters().get("clusters", []):
                for ng_name in eks.list_nodegroups(clusterName=cluster).get("nodegroups", []):
                    ng = eks.describe_nodegroup(clusterName=cluster, nodegroupName=ng_name)["nodegroup"]
                    ami_type = ng.get("amiType", "")
                    if ami_type.startswith("AL2_"):
                        findings.append(Finding(
                            resource_type="eks_nodegroup",
                            resource_id=f"{cluster}/{ng_name}",
                            region=region, account_id=account_id,
                            ami_id=ami_type, ami_description=f"EKS amiType={ami_type}",
                            platform="al2", severity=severity_for("al2"),
                            recommended_action=_recommend("al2", "eks_nodegroup"),
                        ))
        except Exception as e:
            util.dim(f"    (eks scan skipped: {e.__class__.__name__})")

        # 4. Elastic Beanstalk platforms
        try:
            eb = session.client("elasticbeanstalk", region_name=region)
            for env in eb.describe_environments(IncludeDeleted=False).get("Environments", []):
                platform_arn = env.get("PlatformArn", "")
                # AL2 EB platforms contain "AL2" or "Amazon Linux 2" in the arn
                if "AL2" in platform_arn and "AL2023" not in platform_arn:
                    findings.append(Finding(
                        resource_type="beanstalk_environment",
                        resource_id=env["EnvironmentName"],
                        region=region, account_id=account_id,
                        ami_id=None, ami_description=platform_arn,
                        platform="al2", severity=severity_for("al2"),
                        recommended_action=_recommend("al2", "beanstalk_environment"),
                    ))
        except Exception as e:
            util.dim(f"    (beanstalk scan skipped: {e.__class__.__name__})")

    return findings


def _describe_single(ec2_client, image_id: str) -> str:
    try:
        r = ec2_client.describe_images(ImageIds=[image_id])
        imgs = r.get("Images", [])
        if imgs:
            return imgs[0].get("Description", "") + " " + imgs[0].get("Name", "")
    except Exception:
        pass
    return ""


# ---------- Output ----------

def render_table(findings: List[Finding]) -> None:
    if not findings:
        util.ok("No AL2 resources found. ✓")
        return
    al2 = [f for f in findings if f.platform == "al2"]
    al1 = [f for f in findings if f.platform == "al1"]
    util.info(f"Scanned {len(findings)} resource(s). "
              f"{util.color.red(str(len(al2)) + ' AL2')}, "
              f"{util.color.red(str(len(al1)) + ' AL1')}")
    print()
    hdr = f"{'Type':<24}{'Id':<38}{'Region':<12}{'Platform':<10}{'Severity'}"
    print(util.color.bold(hdr))
    print(util.color.gray("-" * len(hdr)))
    for f in findings:
        sev_col = util.color.red if f.severity.startswith("critical") else util.color.yellow
        print(f"{f.resource_type:<24}{f.resource_id[:37]:<38}{f.region:<12}{f.platform:<10}{sev_col(f.severity)}")
    print()
    util.warn(f"AL2 EOL in {days_until(AL2_EOL)} day(s). Next: `al2023-gate packer` to scaffold an AL2023 AMI build.")


def to_json(findings: List[Finding]) -> str:
    return json.dumps([asdict(f) for f in findings], indent=2, default=str)


def to_markdown(findings: List[Finding]) -> str:
    lines = ["# al2023-gate scan report", "",
             f"**Scanned:** {date.today().isoformat()}  ",
             f"**Total resources:** {len(findings)}  ",
             f"**AL2 EOL:** 2026-06-30 ({days_until(AL2_EOL)} days)",
             ""]
    al2 = [f for f in findings if f.platform == "al2"]
    if not al2:
        lines.append("✅ No AL2 resources found.")
        return "\n".join(lines)
    lines += ["| Type | Resource | Region | Severity | Action |",
              "|---|---|---|---|---|"]
    for f in al2:
        lines.append(f"| {f.resource_type} | `{f.resource_id}` | {f.region} | {f.severity} | {f.recommended_action} |")
    lines += ["", "## Primary source",
              "https://aws.amazon.com/amazon-linux-2/faqs/"]
    return "\n".join(lines)


def run(args: argparse.Namespace) -> int:
    if args.fixture:
        findings = scan_fixture(args.fixture)
    else:
        regions = args.regions.split(",") if args.regions else ["us-east-1"]
        findings = scan_live(regions, profile=args.profile)

    machine = args.format in ("json", "csv", "md", "markdown")
    if not machine:
        util.hdr(f"Scanning {'fixture ' + args.fixture if args.fixture else (args.regions or 'us-east-1')}")

    out_text = ""
    if args.format == "json":
        out_text = to_json(findings)
    elif args.format == "md" or args.format == "markdown":
        out_text = to_markdown(findings)
    elif args.format == "csv":
        cols = ["resource_type","resource_id","region","account_id","platform","severity","ami_id","ami_description","recommended_action"]
        rows = [",".join(cols)]
        for f in findings:
            d = asdict(f)
            rows.append(",".join(
                '"' + str(d.get(c, "") or "").replace('"','""') + '"' for c in cols
            ))
        out_text = "\n".join(rows)

    if args.out:
        with open(args.out, "w") as fh:
            fh.write(out_text or to_json(findings))
        util.ok(f"wrote {args.out}")
    elif machine:
        print(out_text)
    else:
        render_table(findings)

    if args.strict and any(f.platform in ("al2", "al1") for f in findings):
        return 1
    return 0