"""Shared utilities: coloring, logging, arg helpers."""
from __future__ import annotations
import os
import sys

_isatty = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def _c(code: str, s: str) -> str:
    return f"\x1b[{code}m{s}\x1b[0m" if _isatty else s


class color:
    red = staticmethod(lambda s: _c("31", s))
    green = staticmethod(lambda s: _c("32", s))
    yellow = staticmethod(lambda s: _c("33", s))
    cyan = staticmethod(lambda s: _c("36", s))
    magenta = staticmethod(lambda s: _c("35", s))
    gray = staticmethod(lambda s: _c("90", s))
    bold = staticmethod(lambda s: _c("1", s))


def info(msg: str) -> None:  print(f"{color.cyan('ℹ')} {msg}")
def ok(msg: str) -> None:    print(f"{color.green('✓')} {msg}")
def warn(msg: str) -> None:  print(f"{color.yellow('⚠')} {msg}")
def err(msg: str) -> None:   print(f"{color.red('✗')} {msg}", file=sys.stderr)
def hdr(msg: str) -> None:   print(f"\n{color.bold(color.magenta('▸ ' + msg))}")
def dim(msg: str) -> None:   print(color.gray(msg))


def dry_run_banner(apply: bool) -> None:
    if not apply:
        warn(color.bold("DRY RUN — no changes written. Pass --apply to execute."))


def is_dry_run(args) -> bool:
    if os.environ.get("AL2023_GATE_DRY_RUN") == "1":
        return True
    return not bool(getattr(args, "apply", False))