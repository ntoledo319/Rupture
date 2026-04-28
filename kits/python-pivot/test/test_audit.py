"""Test native-wheel audit."""
import json
from argparse import Namespace
from pathlib import Path

import pytest

from python_pivot import audit

FIXTURE = Path(__file__).parent / "fixtures" / "requirements.txt"


def _args(path, fmt="table", strict=False):
    return Namespace(path=str(path), format=fmt, strict=strict)


def test_parse_requirements():
    pkgs = audit.parse_requirements(FIXTURE)
    names = [n for n, _ in pkgs]
    assert "numpy" in names
    assert "boto3" in names


def test_detects_outdated_numpy():
    pkgs = audit.parse_requirements(FIXTURE)
    findings = audit.audit_packages(pkgs)
    numpy_finding = next((f for f in findings if f["package"] == "numpy"), None)
    assert numpy_finding is not None
    assert numpy_finding["severity"] == "high"


def test_detects_dead_python_snappy():
    pkgs = audit.parse_requirements(FIXTURE)
    findings = audit.audit_packages(pkgs)
    snappy = next((f for f in findings if f["package"] == "python-snappy"), None)
    assert snappy is not None
    assert snappy["severity"] == "critical"


def test_ignores_clean_requests():
    # requests is NOT in the native wheel table (pure Python) — should not flag
    pkgs = audit.parse_requirements(FIXTURE)
    findings = audit.audit_packages(pkgs)
    assert not any(f["package"] == "requests" for f in findings)


def test_run_strict_exits_nonzero(capsys):
    rc = audit.run(_args(FIXTURE, strict=True))
    assert rc == 1


def test_run_json(capsys):
    rc = audit.run(_args(FIXTURE, fmt="json"))
    assert rc == 0  # non-strict
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert len(parsed) > 0


def test_clean_requirements_pass(tmp_path, capsys):
    clean = tmp_path / "req.txt"
    clean.write_text("numpy==1.26.1\nboto3==1.34.0\nrequests==2.31.0\n")
    rc = audit.run(_args(clean, strict=True))
    assert rc == 0


def test_pyproject_parsing(tmp_path):
    pp = tmp_path / "pyproject.toml"
    pp.write_text('''
[project]
dependencies = [
  "numpy==1.24.0",
  "requests>=2.31"
]
''')
    pkgs = audit.parse_pyproject(pp)
    names = [n for n, _ in pkgs]
    assert "numpy" in names
    assert "requests" in names