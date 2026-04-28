"""Codemod runner: rewrite Python source for 3.9/3.10/3.11 → 3.12 compatibility.

Rules target the actual breakage points, not the entire pyupgrade surface:

  1. collections.abc imports — `from collections import Mapping/MutableMapping/...`
     still works in 3.9 but is removed in 3.10+. Already removed; migration-relevant.
  2. `distutils` imports — removed in 3.12.
  3. `asyncio.coroutine` decorator — removed in 3.11.
  4. `@asyncio.get_event_loop()` at module scope without running loop — deprecated in 3.10,
     removed in 3.12. Lint only; rewrite too risky.
  5. `imp` module — removed in 3.12.
  6. `typing.io` / `typing.re` — removed in 3.12.
  7. `unittest.makeSuite` / `findTestCases` — removed in 3.12.
  8. datetime.utcnow() / utcfromtimestamp() — deprecated in 3.12, lint.
  9. `from __future__ import annotations` — informational (harmless, but no longer needed).
"""
from __future__ import annotations
import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Callable

from . import util


@dataclass
class Rule:
    name: str
    kind: str  # "rewrite" | "lint"
    pattern: re.Pattern
    replacement: str = ""
    reason: str = ""


REWRITE_RULES: List[Rule] = [
    # collections → collections.abc (only for the known ABC names)
    Rule(
        name="collections-abc-imports",
        kind="rewrite",
        pattern=re.compile(
            r"^(from\s+collections\s+import\s+)((?:Mapping|MutableMapping|Sequence|MutableSequence|"
            r"Set|MutableSet|Iterable|Iterator|Container|Hashable|Sized|Callable|"
            r"Awaitable|Coroutine|AsyncIterable|AsyncIterator|Reversible|Generator)"
            r"(?:\s*,\s*(?:Mapping|MutableMapping|Sequence|MutableSequence|Set|MutableSet|"
            r"Iterable|Iterator|Container|Hashable|Sized|Callable|Awaitable|Coroutine|"
            r"AsyncIterable|AsyncIterator|Reversible|Generator))*)(\s*(?:#[^\n]*)?)$",
            re.MULTILINE,
        ),
        replacement=r"from collections.abc import \2\3",
        reason="`collections.Mapping` etc. moved to `collections.abc` in 3.10+.",
    ),
]


LINT_RULES: List[Rule] = [
    Rule(
        name="distutils-import",
        kind="lint",
        pattern=re.compile(r"^\s*(?:from\s+distutils\S*\s+import|import\s+distutils\S*)", re.MULTILINE),
        reason="`distutils` removed in Python 3.12. Use `setuptools`, `packaging`, or `shutil`.",
    ),
    Rule(
        name="imp-module",
        kind="lint",
        pattern=re.compile(r"^\s*import\s+imp\b|^\s*from\s+imp\s+import", re.MULTILINE),
        reason="`imp` module removed in 3.12. Use `importlib` instead.",
    ),
    Rule(
        name="asyncio-coroutine-decorator",
        kind="lint",
        pattern=re.compile(r"@asyncio\.coroutine\b"),
        reason="`@asyncio.coroutine` removed in 3.11. Use `async def` instead.",
    ),
    Rule(
        name="typing-io-re",
        kind="lint",
        pattern=re.compile(r"from\s+typing\s+import\s+[^\n]*\b(IO|BinaryIO|TextIO|Match|Pattern)\b"),
        reason="`typing.IO`/`BinaryIO`/`TextIO` still fine; `typing.io` and `typing.re` submodules removed in 3.12.",
    ),
    Rule(
        name="typing-io-submodule",
        kind="lint",
        pattern=re.compile(r"from\s+typing\.(io|re)\s+import|import\s+typing\.(io|re)\b"),
        reason="`typing.io` and `typing.re` submodules removed in 3.12. Import from `typing` directly.",
    ),
    Rule(
        name="datetime-utcnow",
        kind="lint",
        pattern=re.compile(r"\bdatetime\.utcnow\(\)|\bdatetime\.utcfromtimestamp\("),
        reason="`datetime.utcnow()` deprecated in 3.12. Use `datetime.now(timezone.utc)`.",
    ),
    Rule(
        name="unittest-makesuite",
        kind="lint",
        pattern=re.compile(r"\bunittest\.(makeSuite|findTestCases|getTestCaseNames)\s*\("),
        reason="`unittest.makeSuite`/`findTestCases`/`getTestCaseNames` removed in 3.12.",
    ),
    Rule(
        name="asyncio-get-event-loop",
        kind="lint",
        pattern=re.compile(r"\basyncio\.get_event_loop\s*\(\)"),
        reason="`asyncio.get_event_loop()` deprecated if no running loop; removed in 3.12. Use `asyncio.new_event_loop()` or `asyncio.run()`.",
    ),
    Rule(
        name="pkg-resources",
        kind="lint",
        pattern=re.compile(r"^\s*import\s+pkg_resources\b|^\s*from\s+pkg_resources\s+import", re.MULTILINE),
        reason="`pkg_resources` slow and deprecated. Use `importlib.metadata` or `importlib.resources`.",
    ),
]


def apply_rewrites(text: str) -> Tuple[str, List[dict]]:
    """Return (new_text, edits). edits[i] = {'rule', 'count'}."""
    edits: List[dict] = []
    new_text = text
    for r in REWRITE_RULES:
        new_text, n = r.pattern.subn(r.replacement, new_text)
        if n > 0:
            edits.append({"rule": r.name, "count": n, "kind": "rewrite", "reason": r.reason})
    return new_text, edits


def apply_lints(text: str) -> List[dict]:
    findings: List[dict] = []
    for r in LINT_RULES:
        for m in r.pattern.finditer(text):
            line = text[:m.start()].count("\n") + 1
            # Grab the source line for context
            start = text.rfind("\n", 0, m.start()) + 1
            end = text.find("\n", m.end())
            if end < 0:
                end = len(text)
            findings.append({
                "rule": r.name,
                "line": line,
                "source": text[start:end].rstrip(),
                "reason": r.reason,
                "kind": "lint",
            })
    return findings


def _walk_python_files(root: Path) -> List[Path]:
    if root.is_file():
        return [root]
    out = []
    for p in root.rglob("*.py"):
        if any(part in {".venv", "venv", "__pycache__", ".git", "node_modules"} for part in p.parts):
            continue
        out.append(p)
    return out


def run(args: argparse.Namespace) -> int:
    root = Path(args.path)
    if not root.exists():
        util.err(f"path not found: {root}")
        return 2

    files = _walk_python_files(root)
    apply_mode = bool(args.apply)
    util.hdr(f"Python codemod · {root} · {util.color.red('APPLY') if apply_mode else util.color.yellow('DRY-RUN')}")
    util.dry_run_banner(apply_mode)
    util.dim(f"  {len(files)} file(s) scanned")

    total_rewrites = 0
    total_lints = 0
    files_changed = 0

    for f in files:
        try:
            text = f.read_text()
        except Exception as e:
            util.warn(f"skip {f}: {e}")
            continue

        new_text, rw_edits = apply_rewrites(text)
        lt_findings = apply_lints(new_text)

        if not rw_edits and not lt_findings:
            continue

        if rw_edits:
            files_changed += 1
            for e in rw_edits:
                total_rewrites += e["count"]
                util.info(f"{util.color.green('[rewrite]')} {f} · {e['rule']} · {e['count']} hit(s)")

        for lt in lt_findings:
            total_lints += 1
            util.info(f"{util.color.yellow('[lint]')}    {f}:{lt['line']} · {lt['rule']} — {lt['reason']}")

        if apply_mode and new_text != text:
            f.write_text(new_text)

    print()
    util.ok(f"{total_rewrites} rewrite(s) across {files_changed} file(s), {total_lints} lint finding(s).")

    if not apply_mode and total_rewrites > 0:
        util.info("Re-run with --apply to write changes.")

    if args.strict and (total_rewrites > 0 or total_lints > 0):
        return 1
    return 0