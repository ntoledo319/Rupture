"""
cloud-init diff: compares a user-data script written for AL2 against a set of
known-breaking changes in AL2023. Reports incompatibilities and suggests fixes.

Does NOT rewrite automatically — cloud-init scripts are too sensitive to
blind rewrites. Instead emits an actionable list of locations and suggested edits.
"""
from __future__ import annotations
import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Pattern
from . import util


@dataclass
class Rule:
    name: str
    pattern: Pattern
    message: str
    suggestion: str
    severity: str = "high"


RULES: List[Rule] = [
    Rule(
        name="yum-to-dnf",
        pattern=re.compile(r"\byum\s+(install|update|remove|info|search|clean|list|check-update)\b"),
        message="`yum` still works as a compat alias on AL2023 but is deprecated.",
        suggestion="Replace `yum` with `dnf` for forward compatibility.",
        severity="medium",
    ),
    Rule(
        name="amazon-linux-extras",
        pattern=re.compile(r"\bamazon-linux-extras\b"),
        message="`amazon-linux-extras` does NOT exist on AL2023.",
        suggestion="Move the packages to mainline dnf install commands (see `al2023-gate remap`).",
        severity="critical",
    ),
    Rule(
        name="python2-shebang",
        pattern=re.compile(r"#!\s*/usr/bin/python\b(?![0-9])"),
        message="Python 2 is removed. `#!/usr/bin/python` will 404 on AL2023.",
        suggestion="Use `#!/usr/bin/env python3` or `#!/usr/bin/python3.11`.",
        severity="critical",
    ),
    Rule(
        name="ntp-service",
        pattern=re.compile(r"\bsystemctl\s+(start|enable|restart|status)\s+ntpd\b"),
        message="`ntpd` is not installed by default on AL2023 (chrony replaces it).",
        suggestion="Use `systemctl enable --now chronyd` and remove ntpd package references.",
        severity="high",
    ),
    Rule(
        name="iptables-service",
        pattern=re.compile(r"\bsystemctl\s+(start|enable)\s+iptables\b"),
        message="`iptables` service is not installed by default (nftables is the default firewall).",
        suggestion="Either install iptables-legacy (`dnf install iptables-legacy`) or migrate to nftables.",
        severity="high",
    ),
    Rule(
        name="init-d-service",
        pattern=re.compile(r"/etc/init\.d/"),
        message="SysV init scripts are not supported on AL2023 (same as AL2, but some legacy scripts linger).",
        suggestion="Use `systemctl` + unit files in /etc/systemd/system/.",
        severity="medium",
    ),
    Rule(
        name="rhel-openssl-10",
        pattern=re.compile(r"openssl-?1\.0"),
        message="OpenSSL 1.0 is gone. AL2023 ships OpenSSL 3 — breaking ABI change.",
        suggestion="Rebuild any native code linked against 1.0. Use `openssl3` features or install compat shim.",
        severity="high",
    ),
    Rule(
        name="selinux-permissive-default",
        pattern=re.compile(r"\bSELINUX=(disabled|permissive)\b"),
        message="AL2023 enforces SELinux by default in `enforcing` mode.",
        suggestion="Audit workloads before enabling; add proper policies. Do NOT disable in production.",
        severity="medium",
    ),
    Rule(
        name="repo-mirrorlist",
        pattern=re.compile(r"mirrorlist=https?://mirror(list)?\.centos"),
        message="CentOS mirrorlists won't work on AL2023.",
        suggestion="Use the AL2023 baseurl: `https://cdn.amazonlinux.com/al2023/core/mirrors/`",
        severity="critical",
    ),
    Rule(
        name="cloud-init-config-drive",
        pattern=re.compile(r"\bdatasource_list\s*:\s*\[\s*ConfigDrive"),
        message="AL2023's cloud-init defaults have changed; ConfigDrive is lower priority.",
        suggestion="Review datasource list; prefer Ec2 + NoCloud as defaults.",
        severity="medium",
    ),
    Rule(
        name="yum-config-manager",
        pattern=re.compile(r"\byum-config-manager\b"),
        message="`yum-config-manager` is replaced by `dnf config-manager`.",
        suggestion="Replace with `dnf config-manager` (install `dnf-utils` if missing).",
        severity="medium",
    ),
    Rule(
        name="rpm-key-import-curl",
        pattern=re.compile(r"rpm\s+--import\s+http://"),
        message="HTTP (not HTTPS) key import — insecure AND may fail on AL2023 due to stricter TLS defaults.",
        suggestion="Switch URL to HTTPS and verify the fingerprint.",
        severity="high",
    ),
]


def scan_text(text: str) -> List[dict]:
    findings = []
    for rule in RULES:
        for m in rule.pattern.finditer(text):
            before = text[:m.start()]
            line_num = before.count("\n") + 1
            line = text.splitlines()[line_num - 1] if line_num - 1 < len(text.splitlines()) else ""
            findings.append({
                "rule": rule.name,
                "severity": rule.severity,
                "line": line_num,
                "text": line.strip()[:120],
                "message": rule.message,
                "suggestion": rule.suggestion,
            })
    return findings


def run(args: argparse.Namespace) -> int:
    paths = []
    for raw in args.paths:
        p = Path(raw)
        if p.is_dir():
            paths.extend([f for f in p.rglob("*") if f.is_file() and f.suffix in (".sh", ".yaml", ".yml", ".cfg", ".bash") or f.name in ("user-data", "cloud-config")])
        else:
            paths.append(p)

    if not paths:
        util.warn("No input files. Pass one or more files or a directory.")
        return 0

    util.hdr(f"cloud-init diff · {len(paths)} file(s)")
    total_findings = 0
    for p in paths:
        try:
            text = p.read_text()
        except Exception as e:
            util.warn(f"skip {p}: {e}")
            continue
        findings = scan_text(text)
        if not findings:
            util.dim(f"  {p} · clean")
            continue
        total_findings += len(findings)
        print(f"\n{util.color.bold(str(p))}")
        for f in findings:
            sev_col = util.color.red if f["severity"] == "critical" else (
                      util.color.yellow if f["severity"] == "high" else util.color.cyan)
            print(f"  {sev_col('['+f['severity']+']')} line {f['line']}: {f['rule']}")
            print(f"    {util.color.gray(f['text'])}")
            print(f"    → {f['message']}")
            print(f"    ✎ {f['suggestion']}")

    print()
    if total_findings == 0:
        util.ok("No AL2023 compatibility issues found.")
    else:
        util.warn(f"{total_findings} finding(s) across {len(paths)} file(s).")
    if args.strict and total_findings > 0:
        return 1
    return 0