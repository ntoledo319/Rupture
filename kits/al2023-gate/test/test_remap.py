"""Test the package remap module."""

import json
from argparse import Namespace


from al2023_gate import remap


def test_lookup_known_package():
    e = remap.lookup("docker")
    assert e is not None
    assert e.al2023_name == "docker"
    assert e.category == "extras_to_dnf"
    assert e.action_required is True


def test_lookup_unknown_returns_none():
    assert remap.lookup("totally-not-a-real-package") is None


def test_remap_package_list_handles_unknown():
    entries = remap.remap_package_list(["docker", "fake-pkg-xyz"])
    assert len(entries) == 2
    assert entries[0].category == "extras_to_dnf"
    assert entries[1].category == "unknown"


def test_categorize_buckets():
    entries = remap.remap_package_list(["docker", "nginx1", "kernel"])
    buckets = remap.categorize(entries)
    assert "extras_to_dnf" in buckets
    assert "renamed" in buckets
    assert "same" in buckets


def test_run_table_output(capsys):
    args = Namespace(packages=["docker"], file=None, format="table")
    rc = remap.run(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "docker" in out
    assert "extras_to_dnf" in out


def test_run_json_output(capsys):
    args = Namespace(packages=["docker", "python3.8"], file=None, format="json")
    rc = remap.run(args)
    assert rc == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert len(parsed) == 2
    assert parsed[0]["al2_name"] == "docker"
    assert parsed[1]["al2023_name"] == "python3.11"


def test_run_markdown_output(capsys):
    args = Namespace(packages=["nginx1"], file=None, format="md")
    rc = remap.run(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "| AL2 package |" in out
    assert "`nginx1`" in out


def test_run_empty_packages_fails(capsys):
    args = Namespace(packages=[], file=None, format="table")
    rc = remap.run(args)
    assert rc == 1


def test_run_from_file(tmp_path, capsys):
    pkg_file = tmp_path / "pkgs.txt"
    pkg_file.write_text("docker\n# comment\nnginx1\n\n")
    args = Namespace(packages=[], file=str(pkg_file), format="json")
    rc = remap.run(args)
    assert rc == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert len(parsed) == 2
    names = {e["al2_name"] for e in parsed}
    assert names == {"docker", "nginx1"}
