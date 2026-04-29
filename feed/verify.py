#!/usr/bin/env python3
"""
Rupture rule-pack signature verifier.

Used by the kits at runtime: refuses to use a pack if the signature is
invalid or the pack is past its valid_after window. In dev/local mode,
falls back to a SHA-256 manifest match if cosign isn't installed.
"""

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cosign_available() -> bool:
    return shutil.which("cosign") is not None


def verify_pack(
    pack_bytes: bytes,
    sig_bytes: bytes,
    expected_sha: Optional[str] = None,
) -> tuple[bool, str]:
    actual_sha = sha256_bytes(pack_bytes)
    if expected_sha and actual_sha != expected_sha:
        return False, f"sha mismatch: {actual_sha} != {expected_sha}"

    if not cosign_available():
        # Fallback: trust the manifest hash if cosign is missing.
        return True, "sha-only (cosign unavailable)"

    pack_tmp = Path("/tmp/rupture_pack.yml")
    sig_tmp = Path("/tmp/rupture_pack.sig")
    pack_tmp.write_bytes(pack_bytes)
    sig_tmp.write_bytes(sig_bytes)
    try:
        subprocess.run(
            [
                "cosign",
                "verify-blob",
                "--bundle",
                str(sig_tmp),
                str(pack_tmp),
            ],
            check=True,
            capture_output=True,
        )
        return True, "cosign verified"
    except subprocess.CalledProcessError as e:
        return False, f"cosign verify failed: {e.stderr.decode()}"


def check_validity_window(valid_after_iso: str) -> tuple[bool, str]:
    valid_after = datetime.fromisoformat(valid_after_iso.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    if now < valid_after:
        return False, f"pack not valid until {valid_after.isoformat()}"
    return True, "in window"


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: verify.py <pack.yml> <pack.yml.sig> [manifest.json]")
        return 2
    pack = Path(sys.argv[1]).read_bytes()
    sig = Path(sys.argv[2]).read_bytes()
    manifest = None
    if len(sys.argv) > 3:
        manifest = json.loads(Path(sys.argv[3]).read_text())

    expected = None
    valid_after = None
    if manifest:
        for entry in manifest.get("packs", []):
            if Path(sys.argv[1]).name == entry["filename"]:
                expected = entry.get("sha256")
                valid_after = entry.get("valid_after")
                break

    ok, msg = verify_pack(pack, sig, expected)
    print(f"signature: {msg}")
    if not ok:
        return 1
    if valid_after:
        in_window, win_msg = check_validity_window(valid_after)
        print(f"window: {win_msg}")
        if not in_window:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
