#!/usr/bin/env python3
"""
Rupture rule-pack publisher.

Signs every YAML pack in rules/public/ with Sigstore (keyless OIDC),
writes a manifest with valid_after timestamps so the free CLI sees the
pack 7 days after the Org License feed.

Outputs to docs/feed/ for GitHub Pages serving:
  docs/feed/public/<pack>.yml          # current public pack
  docs/feed/public/<pack>.yml.sig      # Sigstore bundle
  docs/feed/public/manifest.json       # versions + valid_after
  docs/feed/private-stub/...           # placeholder served from KV in prod

Sigstore is free, keyless, OIDC-anchored. CI invokes `cosign sign-blob
--yes --bundle <out>` so no private key material exists on disk.
"""

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RULES_PUBLIC = ROOT / "rules" / "public"
RULES_PRIVATE = ROOT / "rules" / "private"
FEED_OUT = ROOT / "docs" / "feed"
PUBLIC_DELAY_DAYS = 7


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def cosign_available() -> bool:
    return shutil.which("cosign") is not None


def sign_pack(path: Path, sig_path: Path) -> bool:
    """Sign a pack with cosign keyless. No-op locally if cosign absent."""
    if not cosign_available():
        sig_path.write_text(
            json.dumps(
                {
                    "warning": "cosign not installed; CI generates real signatures",
                    "sha256": sha256_file(path),
                    "signed_at": datetime.now(timezone.utc).isoformat(),
                },
                indent=2,
            )
        )
        return False
    subprocess.run(
        [
            "cosign",
            "sign-blob",
            "--yes",
            "--bundle",
            str(sig_path),
            str(path),
        ],
        check=True,
    )
    return True


def build_feed() -> dict:
    FEED_OUT.mkdir(parents=True, exist_ok=True)
    public_out = FEED_OUT / "public"
    public_out.mkdir(parents=True, exist_ok=True)
    private_stub = FEED_OUT / "private-stub"
    private_stub.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    public_valid_after = now + timedelta(days=PUBLIC_DELAY_DAYS)

    manifest = {
        "schema": "rupture.feed.v1",
        "generated_at": now.isoformat(),
        "public_valid_after": public_valid_after.isoformat(),
        "public_delay_days": PUBLIC_DELAY_DAYS,
        "packs": [],
    }

    for pack in sorted(RULES_PUBLIC.glob("*.yml")):
        target = public_out / pack.name
        shutil.copy2(pack, target)
        sig = public_out / (pack.name + ".sig")
        signed = sign_pack(target, sig)
        manifest["packs"].append(
            {
                "name": pack.stem,
                "filename": pack.name,
                "sha256": sha256_file(target),
                "signed": signed,
                "url": f"public/{pack.name}",
                "sig_url": f"public/{pack.name}.sig",
                "valid_after": public_valid_after.isoformat(),
            }
        )

    # Private packs are NOT committed to the public feed. We emit a stub
    # listing names only so Org License clients can discover them; the
    # actual content is served from KV in production.
    private_names = []
    if RULES_PRIVATE.exists():
        private_names = [p.stem for p in RULES_PRIVATE.glob("*.yml")]
    (private_stub / "index.json").write_text(
        json.dumps(
            {
                "note": "private packs require Org License; served from Worker /feed/private/* with key auth.",
                "names": private_names,
            },
            indent=2,
        )
    )

    (FEED_OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def main() -> int:
    manifest = build_feed()
    print(f"Published {len(manifest['packs'])} public packs to {FEED_OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
