"""Test IaC patcher."""
from argparse import Namespace
from pathlib import Path

import pytest

from python_pivot import iac

FIX = Path(__file__).parent / "fixtures"


def _args(path, apply=False, strict=False):
    return Namespace(path=str(path), apply=apply, strict=strict)


def test_sam_template_patched(tmp_path):
    f = tmp_path / "template.yaml"
    f.write_text((FIX / "template.yaml").read_text())
    rc = iac.run(_args(f, apply=True))
    assert rc == 0
    patched = f.read_text()
    assert "Runtime: python3.12" in patched
    # already-migrated one should still be there
    assert patched.count("python3.12") >= 3  # globals + 2 functions + existing one


def test_terraform_patched(tmp_path):
    f = tmp_path / "main.tf"
    f.write_text((FIX / "main.tf").read_text())
    rc = iac.run(_args(f, apply=True))
    assert rc == 0
    patched = f.read_text()
    assert 'runtime       = "python3.12"' in patched
    # Existing 3.12 unchanged
    assert 'already-migrated' in patched


def test_cdk_ts_patched(tmp_path):
    f = tmp_path / "stack.ts"
    f.write_text((FIX / "stack.ts").read_text())
    rc = iac.run(_args(f, apply=True))
    assert rc == 0
    patched = f.read_text()
    assert "Runtime.PYTHON_3_12" in patched
    assert "Runtime.PYTHON_3_9" not in patched
    assert "Runtime.PYTHON_3_10" not in patched


def test_dry_run_no_write(tmp_path):
    f = tmp_path / "template.yaml"
    f.write_text((FIX / "template.yaml").read_text())
    original = f.read_text()
    rc = iac.run(_args(f, apply=False))
    assert rc == 0
    assert f.read_text() == original


def test_strict_dry_run_exits_1_when_edits_needed(tmp_path):
    f = tmp_path / "template.yaml"
    f.write_text((FIX / "template.yaml").read_text())
    rc = iac.run(_args(f, apply=False, strict=True))
    assert rc == 1


def test_idempotent(tmp_path):
    f = tmp_path / "template.yaml"
    f.write_text((FIX / "template.yaml").read_text())
    iac.run(_args(f, apply=True))
    first = f.read_text()
    iac.run(_args(f, apply=True))
    second = f.read_text()
    assert first == second