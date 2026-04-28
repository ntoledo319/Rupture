"""Test cloud-init diff detection."""
from argparse import Namespace
from pathlib import Path

import pytest

from al2023_gate import cloudinit


FIXTURE = Path(__file__).parent / "fixtures" / "user-data.sh"


def _args(paths, strict=False):
    return Namespace(paths=paths, strict=strict)


def test_scan_text_detects_all_major_issues():
    text = FIXTURE.read_text()
    findings = cloudinit.scan_text(text)
    rule_names = {f["rule"] for f in findings}
    # Must catch the critical items
    assert "amazon-linux-extras" in rule_names
    assert "python2-shebang" in rule_names
    assert "ntp-service" in rule_names


def test_scan_text_empty_on_clean_script():
    clean = "#!/bin/bash\nset -eux\ndnf install -y curl\nsystemctl enable chronyd\n"
    findings = cloudinit.scan_text(clean)
    assert findings == []


def test_run_reports_findings(capsys):
    rc = cloudinit.run(_args([str(FIXTURE)]))
    assert rc == 0  # Non-strict, so still 0
    out = capsys.readouterr().out
    assert "amazon-linux-extras" in out
    assert "python2-shebang" in out


def test_run_strict_exits_nonzero_with_findings():
    rc = cloudinit.run(_args([str(FIXTURE)], strict=True))
    assert rc == 1


def test_run_clean_file_passes(tmp_path):
    f = tmp_path / "clean.sh"
    f.write_text("#!/bin/bash\ndnf update -y\nsystemctl enable chronyd\n")
    rc = cloudinit.run(_args([str(f)], strict=True))
    assert rc == 0


def test_run_directory_recursive(tmp_path, capsys):
    d = tmp_path / "ud"
    d.mkdir()
    (d / "setup.sh").write_text("#!/bin/bash\nyum install -y python2\n")
    (d / "extra.sh").write_text("#!/bin/bash\nsystemctl enable ntpd\n")
    rc = cloudinit.run(_args([str(d)]))
    assert rc == 0
    out = capsys.readouterr().out
    assert "setup.sh" in out
    assert "extra.sh" in out