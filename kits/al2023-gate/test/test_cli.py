"""Test the CLI entrypoint integration."""
import subprocess
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).parent.parent


def _run(*args, env_extra=None):
    env = {"PYTHONPATH": str(KIT_ROOT / "src"), "NO_COLOR": "1"}
    import os
    env_full = {**os.environ, **env, **(env_extra or {})}
    result = subprocess.run(
        [sys.executable, "-m", "al2023_gate", "--no-banner", *args],
        capture_output=True, text=True, env=env_full, cwd=str(KIT_ROOT)
    )
    return result


def test_help_exits_zero():
    r = _run("--help")
    assert r.returncode == 0
    assert "scan" in r.stdout
    assert "remap" in r.stdout
    assert "packer" in r.stdout
    assert "cloudinit" in r.stdout
    assert "ansible" in r.stdout
    assert "runbook" in r.stdout


def test_version_flag():
    r = _run("--version")
    assert r.returncode == 0
    assert "al2023-gate" in r.stdout


def test_remap_cli_basic():
    r = _run("remap", "docker", "nginx1", "python3.8")
    assert r.returncode == 0
    assert "docker" in r.stdout
    assert "python3.11" in r.stdout


def test_scan_cli_fixture():
    r = _run("scan", "--fixture", "test/fixtures/inventory.json", "--format", "json")
    assert r.returncode == 0
    assert "al2" in r.stdout.lower()


def test_scan_cli_strict_exits_one():
    r = _run("scan", "--fixture", "test/fixtures/inventory.json", "--strict")
    assert r.returncode == 1


def test_runbook_cli():
    r = _run("runbook", "--kind", "eks", "--name", "prod", "--cluster", "prod-cluster")
    assert r.returncode == 0
    assert "prod" in r.stdout