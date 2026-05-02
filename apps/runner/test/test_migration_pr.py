"""
Smoke tests for migration_pr.

These avoid hitting GitHub or running real kits — they exercise pure helpers
(PR body composition, kit dispatch table, etc.) so CI can run without secrets.
"""

import importlib.util
import os

import pytest


def _load_migration_pr():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target = os.path.join(here, "migration_pr.py")
    spec = importlib.util.spec_from_file_location("migration_pr", target)
    if spec is None or spec.loader is None:
        pytest.skip("migration_pr.py not present")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_module_imports():
    mod = _load_migration_pr()
    assert hasattr(mod, "create_migration_pr")
    assert hasattr(mod, "mint_installation_token")
    assert hasattr(mod, "open_pull_request")


def test_kit_command_dispatch():
    mod = _load_migration_pr()
    assert mod._kit_command("lambda-lifeline", "scan", "/tmp/x")[0] == "lambda-lifeline"
    assert "--apply" in mod._kit_command("al2023-gate", "apply", "/tmp/x")
    assert mod._kit_command("python-pivot", "scan", "/tmp/x")[0] == "python-pivot"
    with pytest.raises(ValueError):
        mod._kit_command("unknown-kit", "scan", "/tmp/x")


def test_pr_body_includes_kit_and_findings():
    mod = _load_migration_pr()
    body = mod.generate_pr_body(
        "lambda-lifeline",
        [{"type": "runtime", "file": "template.yaml", "line": 15}],
        "user@example.com",
    )
    assert "lambda-lifeline" in body
    assert "template.yaml" in body
    assert "user@example.com" in body
    assert "Refund Guarantee" in body


def test_extract_pr_number():
    mod = _load_migration_pr()
    assert mod.extract_pr_number("https://github.com/o/r/pull/42") == 42
    assert mod.extract_pr_number("https://github.com/o/r/pull/42/") == 42


def test_create_migration_pr_rejects_bad_repo():
    mod = _load_migration_pr()
    with pytest.raises(ValueError):
        mod.create_migration_pr(repo="not-a-real-repo", email="x@y.z", installation_id="1")
