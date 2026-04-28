"""Test Ansible playbook patcher."""
from argparse import Namespace
from pathlib import Path

import pytest

from al2023_gate import ansible


FIXTURE = Path(__file__).parent / "fixtures" / "playbook.yml"


def _args(path, apply=False, strict=False):
    return Namespace(path=str(path), apply=apply, strict=strict)


def test_patch_text_rewrites_yum_module():
    src = "  - ansible.builtin.yum:\n      name: nginx\n"
    new, edits = ansible.patch_text(src)
    assert "ansible.builtin.dnf" in new
    assert any(e.get("kind") == "rewrite" for e in edits)


def test_dry_run_does_not_write(tmp_path):
    # Copy fixture into tmp so we can check it's unchanged
    pb = tmp_path / "pb.yml"
    pb.write_text(FIXTURE.read_text())
    original = pb.read_text()
    rc = ansible.run(_args(pb, apply=False))
    assert rc == 0
    # File unchanged
    assert pb.read_text() == original


def test_apply_writes_changes(tmp_path):
    pb = tmp_path / "pb.yml"
    pb.write_text(FIXTURE.read_text())
    rc = ansible.run(_args(pb, apply=True))
    assert rc == 0
    # Now should have been patched
    patched = pb.read_text()
    assert "ansible.builtin.dnf" in patched


def test_strict_exits_nonzero_on_findings(tmp_path):
    pb = tmp_path / "pb.yml"
    pb.write_text(FIXTURE.read_text())
    rc = ansible.run(_args(pb, apply=False, strict=True))
    assert rc == 1


def test_clean_playbook_no_edits(tmp_path, capsys):
    pb = tmp_path / "clean.yml"
    pb.write_text(
        "---\n- hosts: all\n  tasks:\n"
        "    - ansible.builtin.dnf:\n        name: nginx\n        state: present\n"
    )
    rc = ansible.run(_args(pb, apply=False))
    assert rc == 0
    out = capsys.readouterr().out
    assert "No Ansible playbook edits needed" in out or "0 edit" in out or "No " in out