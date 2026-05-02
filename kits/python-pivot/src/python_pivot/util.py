"""Shared utilities: coloring, logging."""

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


def info(msg: str, *, to_stderr: bool = False) -> None:
    _stream = sys.stderr if to_stderr else sys.stdout
    print(f"{color.cyan('ℹ')} {msg}", file=_stream)


def ok(msg: str, *, to_stderr: bool = False) -> None:
    _stream = sys.stderr if to_stderr else sys.stdout
    print(f"{color.green('✓')} {msg}", file=_stream)


def warn(msg: str, *, to_stderr: bool = False) -> None:
    _stream = sys.stderr if to_stderr else sys.stdout
    print(f"{color.yellow('⚠')} {msg}", file=_stream)


def err(msg: str) -> None:
    print(f"{color.red('✗')} {msg}", file=sys.stderr)


def hdr(msg: str, *, to_stderr: bool = False) -> None:
    _stream = sys.stderr if to_stderr else sys.stdout
    print(f"\n{color.bold(color.magenta('▸ ' + msg))}", file=_stream)


def dim(msg: str) -> None:
    print(color.gray(msg))


def dry_run_banner(apply: bool, *, to_stderr: bool = False) -> None:
    if not apply:
        warn(
            color.bold("DRY RUN — no changes written. Pass --apply to execute."),
            to_stderr=to_stderr,
        )
