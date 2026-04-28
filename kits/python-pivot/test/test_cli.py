"""Test CLI wiring via subprocess."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).parent.parent


def _run(*args):
    env = {**os.environ, "PYTHONPATH": str(KIT_ROOT / "src"), "NO_COLOR": "1"}
    return subprocess.run(
        [sys.executable, "-m", "python_pivot", "--no-banner", *args],
        capture_output=True, text=True, env=env, cwd=str(KIT_ROOT),
    )


def test_help():
    r = _run("--help")
    assert r.returncode == 0
    for c in ("scan", "codemod", "audit", "iac", "deploy", "rollback"):
        assert c in r.stdout


def test_version():
    r = _run("--version")
    assert r.returncode == 0
    assert "python-pivot" in r.stdout


def test_scan_cli():
    r = _run("scan", "--fixture", "test/fixtures/lambda-inventory.json", "--format", "json")
    assert r.returncode == 0
    assert "payment-webhook" in r.stdout


def test_scan_strict():
    r = _run("scan", "--fixture", "test/fixtures/lambda-inventory.json", "--strict")
    assert r.returncode == 1


def test_audit_cli():
    r = _run("audit", "test/fixtures/requirements.txt", "--format", "json")
    assert r.returncode == 0
    assert "numpy" in r.stdout


def test_deploy_plan_only():
    r = _run("deploy", "--function", "x", "--alias", "live", "--plan-only")
    assert r.returncode == 0
    assert "Canary" in r.stdout