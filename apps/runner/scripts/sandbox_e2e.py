#!/usr/bin/env python3
"""
Sandbox end-to-end smoke for the migration runner.

Runs the full migration_pr flow against ntoledo319/rupture-sandbox using the
GitHub App credentials in the environment. Exits non-zero on any error.

Usage:
  GITHUB_APP_ID=... GITHUB_APP_PRIVATE_KEY="$(cat key.pem)" \
  RUPTURE_SANDBOX_INSTALL_ID=12345 \
  python3 sandbox_e2e.py
"""

from __future__ import annotations

import json
import os
import sys

# Allow running from anywhere; resolve sibling module
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from migration_pr import create_migration_pr  # noqa: E402


def main() -> int:
    repo = os.environ.get("RUPTURE_SANDBOX_REPO", "ntoledo319/rupture-sandbox")
    email = os.environ.get("RUPTURE_SANDBOX_EMAIL", "sandbox@ntoledo319.dev")
    install_id = os.environ.get("RUPTURE_SANDBOX_INSTALL_ID")

    if not install_id:
        print("ERROR: RUPTURE_SANDBOX_INSTALL_ID not set", file=sys.stderr)
        return 2

    for required in ("GITHUB_APP_ID", "GITHUB_APP_PRIVATE_KEY"):
        if not os.environ.get(required):
            print(f"ERROR: {required} not set", file=sys.stderr)
            return 2

    try:
        result = create_migration_pr(repo=repo, email=email, installation_id=install_id)
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        return 1

    print(json.dumps({"ok": True, **result}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
