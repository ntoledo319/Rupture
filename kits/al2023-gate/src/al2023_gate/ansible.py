"""
Ansible playbook patcher — rewrites common AL2-specific patterns to AL2023-safe equivalents.

Safe, narrow rewrites only. Anything ambiguous is flagged for human review.
"""

from __future__ import annotations
import argparse
import re
from pathlib import Path
from typing import List, Tuple
from . import util


# (pattern, replacement, description)
REWRITES: List[Tuple[re.Pattern, str, str]] = [
    (
        re.compile(r"\bansible\.builtin\.yum\b"),
        "ansible.builtin.dnf",
        "yum module → dnf module",
    ),
    (
        re.compile(r"^(\s*)-?\s*yum:\s*$", re.MULTILINE),
        r"\1- dnf:",
        "yum task → dnf task (top-level)",
    ),
    (
        re.compile(
            r"^\s*(-\s*)?name:\s*Install via amazon-linux-extras.*$\n.*amazon-linux-extras.*",
            re.MULTILINE,
        ),
        "# REMOVED: amazon-linux-extras — migrate to mainline dnf. See al2023-gate remap.",
        "amazon-linux-extras block",
    ),
    (
        re.compile(r"\bpython_version:\s*['\"]?2['\"]?\b"),
        "python_version: '3'",
        "python 2 target → python 3",
    ),
    (
        re.compile(r"/usr/bin/python(?![0-9])"),
        "/usr/bin/python3",
        "bare python interpreter path",
    ),
    (
        re.compile(r"ansible_python_interpreter:\s*/usr/bin/python(?!\d)"),
        "ansible_python_interpreter: /usr/bin/python3",
        "ansible_python_interpreter",
    ),
]

LINT_ONLY: List[Tuple[re.Pattern, str]] = [
    (
        re.compile(r"\byum_repository\s*:"),
        "Consider `dnf` repository module. `yum_repository` still works but is AL2-era.",
    ),
    (
        re.compile(r"\bselinux:\s*state:\s*(disabled|permissive)"),
        "AL2023 enforces SELinux by default. Disabling is a security regression — flagged for review.",
    ),
    (
        re.compile(r"\bservice:\s*name:\s*ntpd\b"),
        "ntpd is not on AL2023 by default. Use chrony.",
    ),
    (
        re.compile(r"\bservice:\s*name:\s*iptables\b"),
        "iptables service not default on AL2023 (nftables is).",
    ),
]


def patch_text(text: str) -> Tuple[str, List[dict]]:
    changed = text
    edits = []
    for pat, repl, desc in REWRITES:
        matches = list(pat.finditer(changed))
        if matches:
            changed = pat.sub(repl, changed)
            edits.append({"kind": "rewrite", "rule": desc, "count": len(matches)})
    for pat, note in LINT_ONLY:
        matches = list(pat.finditer(changed))
        if matches:
            for m in matches:
                line = changed[: m.start()].count("\n") + 1
                edits.append({"kind": "lint", "rule": note, "line": line})
    return changed, edits


def find_playbook_files(root: Path) -> List[Path]:
    if root.is_file():
        return [root]
    out = []
    for f in root.rglob("*"):
        if not f.is_file():
            continue
        if f.suffix in (".yml", ".yaml") and any(
            kw in f.read_text(errors="ignore") for kw in ("hosts:", "tasks:", "- name:")
        ):
            out.append(f)
    return out


def run(args: argparse.Namespace) -> int:
    apply_mode = not util.is_dry_run(args)
    util.hdr(
        f"Ansible patcher · {args.path} · {util.color.red('APPLY') if apply_mode else util.color.yellow('DRY-RUN')}"
    )
    util.dry_run_banner(apply_mode)

    files = find_playbook_files(Path(args.path))
    util.dim(f"  {len(files)} playbook-like file(s) found")

    total_edits = 0
    files_changed = 0
    for f in files:
        original = f.read_text()
        new, edits = patch_text(original)
        if not edits:
            continue
        files_changed += 1
        total_edits += len(edits)
        for e in edits:
            if e["kind"] == "rewrite":
                util.info(
                    f"{util.color.green('[rewrite]')} {f} · {e['rule']} · {e['count']} hit(s)"
                )
            else:
                util.info(
                    f"{util.color.yellow('[lint]')}    {f}:{e['line']} · {e['rule']}"
                )
        if apply_mode and new != original:
            f.write_text(new)

    print()
    if files_changed == 0:
        util.ok("No Ansible playbook edits needed.")
    else:
        util.ok(
            f"{files_changed} file(s), {total_edits} edit(s) {'applied' if apply_mode else 'previewed'}."
        )
        if not apply_mode:
            util.info("Re-run with --apply to write changes.")
    if args.strict and total_edits > 0 and not apply_mode:
        return 1
    return 0
