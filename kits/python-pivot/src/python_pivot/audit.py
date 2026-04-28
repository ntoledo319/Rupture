"""Native-wheel audit for requirements.txt / Pipfile / pyproject.

Checks that declared versions have Python 3.12 wheels available on PyPI
(determined by a curated table of the high-blast-radius packages that
historically lagged behind new CPython releases).

This is a deliberate non-exhaustive table — we cover the packages that
actually break Lambda deploys when the runtime moves. Unknown packages
pass silently (they're usually pure-Python).
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import util


@dataclass
class WheelRequirement:
    package: str
    min_version_for_py312: Optional[str]
    note: str = ""


# Curated table — only packages that historically required a version bump
# to get Python 3.12 wheels. Values are the earliest release with working
# cp312 wheels on PyPI for linux x86_64 / linux aarch64.
PY312_WHEEL_TABLE: Dict[str, WheelRequirement] = {
    # Scientific
    "numpy":          WheelRequirement("numpy",          "1.26.0", "1.26+ ships cp312 wheels."),
    "scipy":          WheelRequirement("scipy",          "1.11.4", "1.11.4+ for cp312."),
    "pandas":         WheelRequirement("pandas",         "2.1.1",  "2.1.1+ for cp312."),
    "scikit-learn":   WheelRequirement("scikit-learn",   "1.3.2",  "1.3.2+ for cp312."),
    "matplotlib":     WheelRequirement("matplotlib",     "3.8.0",  "3.8.0+ for cp312."),
    "pillow":         WheelRequirement("pillow",         "10.1.0", "10.1.0+ for cp312."),
    "lxml":           WheelRequirement("lxml",           "4.9.4",  "4.9.4+ for cp312."),

    # Cryptography / auth
    "cryptography":   WheelRequirement("cryptography",   "41.0.5", "41.0.5+ for cp312 (libssl3)."),
    "pycryptodome":   WheelRequirement("pycryptodome",   "3.19.0", "3.19.0+ for cp312."),
    "bcrypt":         WheelRequirement("bcrypt",         "4.1.1",  "4.1.1+ for cp312."),
    "pyopenssl":      WheelRequirement("pyopenssl",      "23.3.0", "23.3.0+ for cp312."),

    # DB drivers
    "psycopg2-binary": WheelRequirement("psycopg2-binary","2.9.9", "2.9.9+ for cp312."),
    "psycopg":        WheelRequirement("psycopg",        "3.1.13", "3.1.13+ for cp312."),
    "mysqlclient":    WheelRequirement("mysqlclient",    "2.2.0",  "2.2.0+ for cp312."),
    "pymssql":        WheelRequirement("pymssql",        "2.2.11", "2.2.11+ for cp312."),

    # Data serialization
    "pyyaml":         WheelRequirement("pyyaml",         "6.0.1",  "6.0.1+ for cp312."),
    "orjson":         WheelRequirement("orjson",         "3.9.10", "3.9.10+ for cp312."),
    "ujson":          WheelRequirement("ujson",          "5.8.0",  "5.8.0+ for cp312."),
    "msgpack":        WheelRequirement("msgpack",        "1.0.7",  "1.0.7+ for cp312."),

    # Web / network
    "aiohttp":        WheelRequirement("aiohttp",        "3.9.0",  "3.9.0+ for cp312."),
    "grpcio":         WheelRequirement("grpcio",         "1.59.0", "1.59.0+ for cp312."),
    "protobuf":       WheelRequirement("protobuf",       "4.25.0", "4.25.0+ for cp312."),
    "frozenlist":     WheelRequirement("frozenlist",     "1.4.0",  "1.4.0+ for cp312."),
    "multidict":      WheelRequirement("multidict",      "6.0.4",  "6.0.4+ for cp312."),
    "yarl":           WheelRequirement("yarl",           "1.9.3",  "1.9.3+ for cp312."),

    # ML / NLP
    "tiktoken":       WheelRequirement("tiktoken",       "0.5.2",  "0.5.2+ for cp312."),
    "tokenizers":     WheelRequirement("tokenizers",     "0.15.0", "0.15.0+ for cp312."),

    # AWS
    "awscrt":         WheelRequirement("awscrt",         "0.19.17","0.19.17+ for cp312."),
    "boto3":          WheelRequirement("boto3",          "1.29.0", "1.29+ tested on cp312."),
    "botocore":       WheelRequirement("botocore",       "1.32.0", "1.32+ tested on cp312."),

    # Dead-end — these never added cp312 wheels
    "python-snappy":  WheelRequirement("python-snappy",  None,     "No cp312 wheels. Switch to `cramjam` or `plyvel`."),
    "fastparquet":    WheelRequirement("fastparquet",    "2023.10.1", "2023.10.1+ for cp312."),
}


_REQ_LINE = re.compile(
    r"^\s*([A-Za-z0-9_.\-]+)\s*(?:\[[^\]]*\])?\s*([<>=!~]+.+)?\s*(?:#.*)?$"
)


def parse_requirements(path: Path) -> List[Tuple[str, Optional[str]]]:
    """Parse a requirements.txt-style file. Returns [(pkg_name_lower, specifier or None)]."""
    pkgs: List[Tuple[str, Optional[str]]] = []
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        m = _REQ_LINE.match(line)
        if not m:
            continue
        name = m.group(1).lower()
        spec = (m.group(2) or "").strip() or None
        pkgs.append((name, spec))
    return pkgs


def parse_pyproject(path: Path) -> List[Tuple[str, Optional[str]]]:
    """Best-effort dep extraction from pyproject.toml (regex, no TOML parser dep)."""
    text = path.read_text()
    pkgs: List[Tuple[str, Optional[str]]] = []
    # Look for dependencies = ["pkg==1.2", ...] and optional-dependencies blocks
    for dep_list in re.findall(r'dependencies\s*=\s*\[([^\]]*)\]', text, flags=re.DOTALL):
        for m in re.finditer(r'"\s*([A-Za-z0-9_.\-]+)\s*(?:\[[^\]]*\])?\s*([<>=!~][^"]*)?\s*"', dep_list):
            pkgs.append((m.group(1).lower(), (m.group(2) or "").strip() or None))
    return pkgs


def _extract_min_version(spec: Optional[str]) -> Optional[str]:
    """From a spec like '==1.2.0,>1.0' or '>=3.9' extract the pinned or lower-bound version."""
    if not spec:
        return None
    for op in ("==", ">="):
        for part in spec.split(","):
            part = part.strip()
            if part.startswith(op):
                return part[len(op):].strip()
    return None


def _version_tuple(v: str) -> tuple:
    """Naive version comparison — splits dots, zfills numeric parts."""
    out = []
    for part in re.split(r"[.\-+]", v):
        if part.isdigit():
            out.append(int(part))
        else:
            # suffix like a1, rc2 — treat as slightly less than equivalent numeric
            num = re.match(r"(\d+)", part)
            out.append(int(num.group(1)) if num else 0)
    return tuple(out)


def _version_lt(a: str, b: str) -> bool:
    return _version_tuple(a) < _version_tuple(b)


def audit_packages(pkgs: List[Tuple[str, Optional[str]]]) -> List[dict]:
    """Return list of findings for packages that need an upgrade or are unavailable on py3.12."""
    findings: List[dict] = []
    for name, spec in pkgs:
        req = PY312_WHEEL_TABLE.get(name)
        if not req:
            continue  # unknown — assume fine
        declared = _extract_min_version(spec)
        if req.min_version_for_py312 is None:
            # Package has NO cp312 wheels — always a problem
            findings.append({
                "package": name,
                "declared": spec or "(unpinned)",
                "required": "(none — no cp312 wheels)",
                "severity": "critical",
                "note": req.note,
            })
            continue
        if declared is None:
            # unpinned — flag as warning (latest will likely resolve, but reproducibility is at risk)
            findings.append({
                "package": name,
                "declared": "(unpinned)",
                "required": f">={req.min_version_for_py312}",
                "severity": "low",
                "note": f"unpinned; latest will include cp312 wheels. Pin >={req.min_version_for_py312} for reproducibility.",
            })
            continue
        if _version_lt(declared, req.min_version_for_py312):
            findings.append({
                "package": name,
                "declared": spec,
                "required": f">={req.min_version_for_py312}",
                "severity": "high",
                "note": req.note,
            })
    return findings


def run(args: argparse.Namespace) -> int:
    p = Path(args.path)
    if not p.exists():
        util.err(f"path not found: {p}")
        return 2

    machine = args.format == "json"

    if not machine:
        util.hdr(f"Native-wheel audit · {p}")

    if p.suffix == ".toml" or p.name == "pyproject.toml":
        pkgs = parse_pyproject(p)
    else:
        pkgs = parse_requirements(p)

    findings = audit_packages(pkgs)

    if args.format == "json":
        print(json.dumps(findings, indent=2))
        return 1 if (args.strict and findings) else 0

    if not findings:
        util.ok(f"All {len(pkgs)} pinned package(s) OK for Python 3.12.")
        return 0

    for f in findings:
        sev_color = util.color.red if f["severity"] == "critical" else (
                    util.color.yellow if f["severity"] == "high" else util.color.cyan)
        print(f"  {sev_color('[' + f['severity'] + ']')} {util.color.bold(f['package'])} "
              f"declared={f['declared']} · needs {f['required']}")
        print(f"      {util.color.gray(f['note'])}")

    util.warn(f"{len(findings)} package(s) need attention before Python 3.12.")

    return 1 if (args.strict and findings) else 0