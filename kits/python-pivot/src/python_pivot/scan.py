"""Lambda Python runtime scanner. Works live (boto3) or from a fixture JSON.

Fixture shape: {"functions": [{"FunctionName":..., "Runtime":..., "Region":..., ...}]}
"""

from __future__ import annotations
import argparse
import json
from dataclasses import dataclass, asdict
from typing import List, Optional

from . import util
from .runtimes import RUNTIME_TABLE, days_until, severity_for, is_eol_or_soon


@dataclass
class Finding:
    function_name: str
    runtime: str
    region: str
    arn: str
    severity: str
    days_to_eol: Optional[int]
    recommended_runtime: str


def scan_fixture(path: str) -> List[Finding]:
    with open(path) as f:
        data = json.load(f)
    out: List[Finding] = []
    for fn in data.get("functions", []):
        rt = fn.get("Runtime", "unknown")
        info = RUNTIME_TABLE.get(rt)
        out.append(
            Finding(
                function_name=fn.get("FunctionName", ""),
                runtime=rt,
                region=fn.get("Region", "us-east-1"),
                arn=fn.get("FunctionArn", ""),
                severity=severity_for(rt),
                days_to_eol=(
                    days_until(info.deprecation_phase1)
                    if info and info.deprecation_phase1
                    else None
                ),
                recommended_runtime=info.recommended_target if info else "python3.12",
            )
        )
    return out


def scan_live(regions: List[str], profile: Optional[str] = None) -> List[Finding]:
    try:
        import boto3
    except ImportError:
        util.err("boto3 not installed. Run: pip install 'python-pivot[aws]'")
        raise SystemExit(2)

    session = boto3.Session(profile_name=profile) if profile else boto3.Session()
    findings: List[Finding] = []

    for region in regions:
        client = session.client("lambda", region_name=region)
        paginator = client.get_paginator("list_functions")
        for page in paginator.paginate():
            for fn in page.get("Functions", []):
                rt = fn.get("Runtime", "")
                if not rt.startswith("python"):
                    continue
                info = RUNTIME_TABLE.get(rt)
                findings.append(
                    Finding(
                        function_name=fn["FunctionName"],
                        runtime=rt,
                        region=region,
                        arn=fn["FunctionArn"],
                        severity=severity_for(rt),
                        days_to_eol=(
                            days_until(info.deprecation_phase1)
                            if info and info.deprecation_phase1
                            else None
                        ),
                        recommended_runtime=(
                            info.recommended_target if info else "python3.12"
                        ),
                    )
                )
    return findings


# ---------------- rendering ----------------


def render_table(findings: List[Finding]) -> str:
    if not findings:
        return "No Python Lambda functions found."
    c1 = max(len("FUNCTION"), max(len(f.function_name) for f in findings))
    c2 = max(len("RUNTIME"), max(len(f.runtime) for f in findings))
    c3 = max(len("REGION"), max(len(f.region) for f in findings))
    c4 = max(len("SEVERITY"), max(len(f.severity) for f in findings))
    header = f"{'FUNCTION':<{c1}}  {'RUNTIME':<{c2}}  {'REGION':<{c3}}  {'SEVERITY':<{c4}}  DAYS-TO-EOL  TARGET"
    sep = "-" * len(header)
    lines = [header, sep]
    for f in findings:
        d = "—" if f.days_to_eol is None else str(f.days_to_eol)
        lines.append(
            f"{f.function_name:<{c1}}  {f.runtime:<{c2}}  {f.region:<{c3}}  {f.severity:<{c4}}  {d:>11}  {f.recommended_runtime}"
        )
    return "\n".join(lines)


def render_json(findings: List[Finding]) -> str:
    return json.dumps([asdict(f) for f in findings], indent=2)


def render_csv(findings: List[Finding]) -> str:
    cols = [
        "function_name",
        "runtime",
        "region",
        "arn",
        "severity",
        "days_to_eol",
        "recommended_runtime",
    ]
    lines = [",".join(cols)]
    for f in findings:
        row = [str(getattr(f, c) if getattr(f, c) is not None else "") for c in cols]
        escaped = ['"' + x.replace('"', '""') + '"' for x in row]
        lines.append(",".join(escaped))
    return "\n".join(lines)


def render_markdown(findings: List[Finding]) -> str:
    lines = [
        "| Function | Runtime | Region | Severity | Days to EOL | Recommended |",
        "|---|---|---|---|---|---|",
    ]
    for f in findings:
        d = "—" if f.days_to_eol is None else str(f.days_to_eol)
        lines.append(
            f"| `{f.function_name}` | {f.runtime} | {f.region} | {f.severity} | {d} | {f.recommended_runtime} |"
        )
    return "\n".join(lines)


# ---------------- CLI entry ----------------


def run(args: argparse.Namespace) -> int:
    machine = args.format in ("json", "csv", "md", "markdown")

    if args.fixture:
        findings = scan_fixture(args.fixture)
        source = f"fixture {args.fixture}"
    else:
        regions = [
            r.strip() for r in (args.regions or "us-east-1").split(",") if r.strip()
        ]
        findings = scan_live(regions, profile=args.profile)
        source = ",".join(regions)

    if not machine:
        util.hdr(f"Scanning {source}", to_stderr=False)
        eol = [f for f in findings if is_eol_or_soon(f.runtime)]
        util.info(
            f"Scanned {len(findings)} Python Lambda function(s). {len(eol)} need migration."
        )

    if args.format == "json":
        out = render_json(findings)
    elif args.format == "csv":
        out = render_csv(findings)
    elif args.format in ("md", "markdown"):
        out = render_markdown(findings)
    else:
        out = render_table(findings)

    if args.out:
        with open(args.out, "w") as f:
            f.write(out)
        util.ok(f"wrote {args.out}")
    else:
        print(out)

    if not machine:
        worst = next(
            (f for f in findings if f.severity in ("critical", "critical-eol")), None
        )
        if worst and worst.days_to_eol is not None:
            util.warn(
                f"{worst.runtime} hits EOL in {worst.days_to_eol} day(s). Next: `python-pivot codemod`"
            )

    if args.strict and any(is_eol_or_soon(f.runtime) for f in findings):
        return 1
    return 0
