"""Test Python codemod."""
from argparse import Namespace
from pathlib import Path

import pytest

from python_pivot import codemod

FIXTURE = Path(__file__).parent / "fixtures" / "sample_source.py"


def _args(path, apply=False, strict=False):
    return Namespace(path=str(path), apply=apply, strict=strict)


def test_apply_rewrites_collections_import():
    src = "from collections import Mapping, MutableMapping\n"
    new, edits = codemod.apply_rewrites(src)
    assert "from collections.abc import Mapping, MutableMapping" in new
    assert edits[0]["rule"] == "collections-abc-imports"


def test_apply_rewrites_preserves_unrelated():
    src = "from collections import OrderedDict, defaultdict\n"
    new, edits = codemod.apply_rewrites(src)
    # OrderedDict/defaultdict are NOT in abc — should not be touched
    assert new == src
    assert edits == []


def test_apply_lints_catches_distutils():
    src = "from distutils.util import strtobool\n"
    findings = codemod.apply_lints(src)
    assert any(f["rule"] == "distutils-import" for f in findings)


def test_apply_lints_catches_imp():
    src = "import imp\n"
    findings = codemod.apply_lints(src)
    assert any(f["rule"] == "imp-module" for f in findings)


def test_apply_lints_catches_asyncio_coroutine():
    src = "@asyncio.coroutine\ndef f():\n    pass\n"
    findings = codemod.apply_lints(src)
    assert any(f["rule"] == "asyncio-coroutine-decorator" for f in findings)


def test_apply_lints_catches_utcnow():
    src = "datetime.utcnow()\n"
    findings = codemod.apply_lints(src)
    assert any(f["rule"] == "datetime-utcnow" for f in findings)


def test_apply_lints_catches_pkg_resources():
    src = "import pkg_resources\n"
    findings = codemod.apply_lints(src)
    assert any(f["rule"] == "pkg-resources" for f in findings)


def test_dry_run_does_not_modify(tmp_path):
    f = tmp_path / "s.py"
    f.write_text(FIXTURE.read_text())
    original = f.read_text()
    rc = codemod.run(_args(f, apply=False))
    assert rc == 0
    assert f.read_text() == original


def test_apply_writes(tmp_path):
    f = tmp_path / "s.py"
    f.write_text(FIXTURE.read_text())
    rc = codemod.run(_args(f, apply=True))
    assert rc == 0
    patched = f.read_text()
    assert "from collections.abc import Mapping" in patched


def test_strict_exits_nonzero(tmp_path):
    f = tmp_path / "s.py"
    f.write_text(FIXTURE.read_text())
    rc = codemod.run(_args(f, apply=False, strict=True))
    assert rc == 1


def test_clean_file_passes(tmp_path):
    f = tmp_path / "clean.py"
    f.write_text("def handler(event, context):\n    return {'ok': True}\n")
    rc = codemod.run(_args(f, apply=False, strict=True))
    assert rc == 0