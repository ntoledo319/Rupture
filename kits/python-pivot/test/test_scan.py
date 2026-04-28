"""Test Python Lambda runtime scanner."""
import json
from argparse import Namespace
from pathlib import Path

import pytest

from python_pivot import scan

FIXTURE = Path(__file__).parent / "fixtures" / "lambda-inventory.json"


def _args(**kw):
    base = dict(fixture=str(FIXTURE), regions=None, profile=None,
                format="table", out=None, strict=False)
    base.update(kw)
    return Namespace(**base)


def test_loads_all_six():
    findings = scan.scan_fixture(str(FIXTURE))
    assert len(findings) == 6


def test_identifies_eol_runtimes():
    findings = scan.scan_fixture(str(FIXTURE))
    by_rt = {f.runtime: f for f in findings}
    # 3.7 is long past EOL
    assert by_rt["python3.7"].severity == "critical-eol"
    # 3.8 is past EOL  
    assert by_rt["python3.8"].severity == "critical-eol"
    # 3.12 is the target — ok
    assert by_rt["python3.12"].severity == "ok"


def test_run_table_format(capsys):
    rc = scan.run(_args())
    assert rc == 0
    out = capsys.readouterr().out
    assert "payment-webhook" in out
    assert "python3.9" in out


def test_run_json(capsys):
    rc = scan.run(_args(format="json"))
    assert rc == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert len(parsed) == 6
    assert any(x["function_name"] == "payment-webhook" for x in parsed)


def test_run_csv_has_header(capsys):
    rc = scan.run(_args(format="csv"))
    assert rc == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith('function_name')


def test_run_markdown(capsys):
    rc = scan.run(_args(format="md"))
    assert rc == 0
    out = capsys.readouterr().out
    assert "| Function |" in out


def test_strict_mode_exits_1_with_eol():
    rc = scan.run(_args(strict=True))
    assert rc == 1


def test_run_out_file(tmp_path):
    outfile = tmp_path / "f.json"
    rc = scan.run(_args(format="json", out=str(outfile)))
    assert rc == 0
    assert outfile.exists()
    data = json.loads(outfile.read_text())
    assert len(data) == 6