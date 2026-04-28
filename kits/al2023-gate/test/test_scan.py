"""Test the scanner module with a fixture."""
import json
import os
import sys
from argparse import Namespace
from pathlib import Path

import pytest

from al2023_gate import scan

FIXTURE = Path(__file__).parent / "fixtures" / "inventory.json"


def _args(**overrides):
    base = dict(fixture=str(FIXTURE), regions=None, profile=None,
                format="table", out=None, strict=False)
    base.update(overrides)
    return Namespace(**base)


def test_fixture_loads_all_resources():
    findings = scan.scan_fixture(str(FIXTURE))
    assert len(findings) == 6


def test_fixture_classifies_al2_and_al2023():
    findings = scan.scan_fixture(str(FIXTURE))
    al2 = [f for f in findings if f.platform == "al2"]
    al2023 = [f for f in findings if f.platform == "al2023"]
    # 4 AL2, 1 AL2023, 1 "other" (container base which doesn't pattern-match AL2 patterns)
    assert len(al2) == 4
    assert len(al2023) == 1


def test_fixture_severity_medium_or_high():
    findings = scan.scan_fixture(str(FIXTURE))
    severities = {f.severity for f in findings if f.platform == "al2"}
    assert severities.issubset({"medium", "high", "critical", "critical-eol"})


def test_recommendation_populated_for_al2_only():
    findings = scan.scan_fixture(str(FIXTURE))
    for f in findings:
        if f.platform == "al2":
            assert f.recommended_action
            assert "AL2023" in f.recommended_action


def test_run_table_format(capsys):
    rc = scan.run(_args())
    assert rc == 0
    out = capsys.readouterr().out
    assert "Type" in out
    assert "i-0a1b2c3d4e5f60718" in out


def test_run_json_format(capsys):
    rc = scan.run(_args(format="json"))
    assert rc == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert isinstance(parsed, list)
    assert any(x["resource_id"] == "i-0a1b2c3d4e5f60718" for x in parsed)


def test_run_csv_format_has_header(capsys):
    rc = scan.run(_args(format="csv"))
    assert rc == 0
    out = capsys.readouterr().out
    # First row is the header
    first_line = out.strip().splitlines()[0]
    assert "resource_type" in first_line


def test_run_strict_exits_nonzero_when_al2_present(capsys):
    rc = scan.run(_args(strict=True))
    assert rc == 1


def test_run_writes_to_file_when_out_specified(tmp_path, capsys):
    outfile = tmp_path / "findings.json"
    rc = scan.run(_args(format="json", out=str(outfile)))
    assert rc == 0
    assert outfile.exists()
    data = json.loads(outfile.read_text())
    assert len(data) == 6


def test_classify_ami_al2_patterns():
    assert scan.classify_ami("Amazon Linux 2 AMI 2.0.20240318.0") == "al2"
    assert scan.classify_ami("amzn2-ami-kernel-5.10-hvm") == "al2"
    assert scan.classify_ami("Amazon Linux 2023 AMI") == "al2023"
    assert scan.classify_ami(None) == "unknown"