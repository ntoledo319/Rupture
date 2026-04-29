"""IaC patcher: rewrite Python Lambda runtimes in SAM / CDK / Terraform / Serverless."""
from __future__ import annotations
import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from . import util


TARGET_RUNTIME = "python3.12"
DEPRECATED_PY = r"python3\.(?:7|8|9|10|11)"


@dataclass
class RewriteRule:
    name: str
    pattern: re.Pattern
    replacement: str


RULES: List[RewriteRule] = [
    # SAM / CloudFormation YAML: Runtime: python3.9
    RewriteRule(
        name="sam-cfn-runtime",
        pattern=re.compile(rf"(^\s*Runtime\s*:\s*){DEPRECATED_PY}(\s*$)", re.MULTILINE),
        replacement=r"\g<1>" + TARGET_RUNTIME + r"\g<2>",
    ),
    # SAM globals
    RewriteRule(
        name="sam-globals-runtime",
        pattern=re.compile(rf"(Globals\s*:\s*\n(?:[^\n]*\n)*?\s*Runtime\s*:\s*){DEPRECATED_PY}", re.MULTILINE),
        replacement=r"\g<1>" + TARGET_RUNTIME,
    ),
    # CDK (TypeScript and Python): Runtime.PYTHON_3_9, lambda.Runtime.PYTHON_3_9, _lambda.Runtime.PYTHON_3_9
    RewriteRule(
        name="cdk-runtime-enum",
        pattern=re.compile(r"(Runtime\.PYTHON_3_)(7|8|9|10|11)\b"),
        replacement=r"\g<1>12",
    ),
    # Terraform AWS Provider: runtime = "python3.9"
    RewriteRule(
        name="terraform-runtime",
        pattern=re.compile(rf'(runtime\s*=\s*")({DEPRECATED_PY})(")'),
        replacement=r'\g<1>' + TARGET_RUNTIME + r'\g<3>',
    ),
    # Serverless Framework: runtime: python3.9
    RewriteRule(
        name="serverless-runtime",
        pattern=re.compile(rf"(^\s*runtime\s*:\s*){DEPRECATED_PY}(\s*$)", re.MULTILINE),
        replacement=r"\g<1>" + TARGET_RUNTIME + r"\g<2>",
    ),
]


def _walk_iac_files(root: Path) -> List[Path]:
    if root.is_file():
        return [root]
    exts = {".yaml", ".yml", ".ts", ".js", ".tf", ".py", ".json"}
    out = []
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix not in exts:
            continue
        if any(part in {".venv", "venv", "__pycache__", "node_modules", ".git", "cdk.out", ".terraform"}
               for part in p.parts):
            continue
        out.append(p)
    return out


def patch_text(text: str) -> Tuple[str, List[dict]]:
    edits: List[dict] = []
    new = text
    for r in RULES:
        new, n = r.pattern.subn(r.replacement, new)
        if n > 0:
            edits.append({"rule": r.name, "count": n})
    return new, edits


def run(args: argparse.Namespace) -> int:
    root = Path(args.path)
    if not root.exists():
        util.err(f"path not found: {root}")
        return 2

    apply_mode = bool(args.apply)
    util.hdr(f"IaC patcher · {root} · {util.color.red('APPLY') if apply_mode else util.color.yellow('DRY-RUN')}")
    util.dry_run_banner(apply_mode)

    files = _walk_iac_files(root)
    util.dim(f"  {len(files)} IaC candidate file(s) scanned")

    total_edits = 0
    files_changed = 0
    for f in files:
        try:
            text = f.read_text()
        except Exception as e:
            util.warn(f"skip {f}: {e}")
            continue
        new_text, edits = patch_text(text)
        if not edits:
            continue
        files_changed += 1
        for e in edits:
            total_edits += e["count"]
            util.info(f"{util.color.green('[rewrite]')} {f} · {e['rule']} · {e['count']} hit(s)")
        if apply_mode and new_text != text:
            f.write_text(new_text)

    print()
    if files_changed == 0:
        util.ok("No IaC files required runtime rewrites.")
    else:
        util.ok(f"{total_edits} rewrite(s) across {files_changed} file(s).")
        if not apply_mode:
            util.info("Re-run with --apply to write changes.")

    if args.strict and total_edits > 0 and not apply_mode:
        return 1
    return 0