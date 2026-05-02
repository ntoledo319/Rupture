"""Manual rollback: re-point a Lambda alias at its previous version."""

from __future__ import annotations
import argparse

from . import util


def run(args: argparse.Namespace) -> int:
    try:
        import boto3
    except ImportError:
        util.err("boto3 not installed. Run: pip install 'python-pivot[aws]'")
        return 2

    region = args.region or "us-east-1"
    session = (
        boto3.Session(profile_name=args.profile) if args.profile else boto3.Session()
    )
    lam = session.client("lambda", region_name=region)

    util.hdr(f"Rollback alias {args.alias} on {args.function}")

    # Get current alias
    try:
        cur = lam.get_alias(FunctionName=args.function, Name=args.alias)
    except lam.exceptions.ResourceNotFoundException:
        util.err(f"Alias {args.alias} not found on {args.function}")
        return 1

    current_version = cur["FunctionVersion"]
    util.info(f"Current alias version: {current_version}")

    # Find previous numeric version
    versions = []
    paginator = lam.get_paginator("list_versions_by_function")
    for page in paginator.paginate(FunctionName=args.function):
        for v in page["Versions"]:
            if v["Version"] != "$LATEST":
                versions.append(v["Version"])
    versions_sorted = sorted(set(versions), key=lambda x: int(x))
    if len(versions_sorted) < 2:
        util.err(
            f"Only {len(versions_sorted)} version(s) exist — nothing to roll back to."
        )
        return 1

    try:
        idx = versions_sorted.index(current_version)
    except ValueError:
        # alias might be on $LATEST or weighted — fall back to newest-but-one
        idx = len(versions_sorted) - 1

    if idx == 0:
        util.err("Already on oldest version — cannot roll back further.")
        return 1
    target = args.target_version or versions_sorted[idx - 1]

    if not args.apply:
        util.warn(
            f"DRY-RUN — would swap alias {args.alias} from {current_version} → {target}. Pass --apply to execute."
        )
        return 0

    lam.update_alias(
        FunctionName=args.function,
        Name=args.alias,
        FunctionVersion=target,
        RoutingConfig={"AdditionalVersionWeights": {}},
    )
    util.ok(f"Alias {args.alias} now points at version {target}")
    return 0
