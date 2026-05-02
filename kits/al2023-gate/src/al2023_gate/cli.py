"""al2023-gate CLI — entrypoint wiring all subcommands."""

from __future__ import annotations

import argparse
import os
import sys

from . import __version__
from . import util
from . import scan as scan_mod
from . import remap as remap_mod
from . import packer as packer_mod
from . import cloudinit as cloudinit_mod
from . import ansible as ansible_mod
from . import runbook as runbook_mod


BANNER = r"""
    _    _     ____   ___ ____ _____         ____    _  _____ _____
   / \  | |   |___ \ / _ \___ \___ /        / ___|  / \|_   _| ____|
  / _ \ | |     __) | | | |__) ||_ \ _____ | |  _  / _ \ | | |  _|
 / ___ \| |___ / __/| |_| / __/___) |_____|| |_| |/ ___ \| | | |___
/_/   \_\_____|_____|\___/_____|____/       \____/_/   \_\_| |_____|

          AL2023-GATE  •  Amazon Linux 2 → AL2023 migration kit
"""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="al2023-gate",
        description="Amazon Linux 2 → AL2023 migration kit. Scan, remap, build, migrate, rollback.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--version", action="version", version=f"al2023-gate {__version__}")
    p.add_argument("--no-banner", action="store_true", help="Suppress banner")

    sub = p.add_subparsers(dest="cmd", required=True, metavar="COMMAND")

    # scan — matches scan.run(args): args.fixture, args.regions, args.profile, args.format, args.out, args.strict
    s = sub.add_parser(
        "scan", help="Scan AWS for AL2-based compute (EC2, LT, EKS, ECS, Beanstalk)"
    )
    s.add_argument("--profile", help="AWS profile name")
    s.add_argument("--regions", help="Comma-separated AWS regions (default: us-east-1)")
    s.add_argument("--fixture", help="Path to JSON fixture for offline/demo mode")
    s.add_argument(
        "--format", choices=["table", "json", "csv", "md", "markdown"], default="table"
    )
    s.add_argument("--out", help="Write output to file instead of stdout")
    s.add_argument(
        "--strict", action="store_true", help="Exit 1 if AL2 resources found"
    )
    s.set_defaults(func=scan_mod.run)

    # remap
    r = sub.add_parser("remap", help="Map AL2 package names → AL2023 equivalents")
    r.add_argument("packages", nargs="*", help="Package names to remap")
    r.add_argument("--file", help="File with package names (one per line)")
    r.add_argument("--format", choices=["table", "json", "md"], default="table")
    r.set_defaults(func=remap_mod.run)

    # packer — matches packer.run(args)
    pk = sub.add_parser("packer", help="Generate Packer HCL template for AL2023 AMI")
    pk.add_argument("--packages", help="File with package list (one per line)")
    pk.add_argument("--from-list", help="Comma-separated inline package list")
    pk.add_argument(
        "--out", default="./build", help="Output directory for .pkr.hcl + report"
    )
    pk.add_argument("--region", default="us-east-1", help="Build region")
    pk.add_argument(
        "--instance-type", default="t3.small", help="Packer build instance type"
    )
    pk.add_argument("--name", default="al2023-migration", help="AMI name prefix")
    pk.add_argument(
        "--arch", default="x86_64", choices=["x86_64", "arm64"], help="Architecture"
    )
    pk.set_defaults(func=packer_mod.run)

    # cloudinit — matches cloudinit.run(args): args.paths (list)
    ci = sub.add_parser(
        "cloudinit", help="Diff cloud-init / user-data scripts for AL2→AL2023 breakage"
    )
    ci.add_argument("paths", nargs="+", help="One or more files or directories")
    ci.add_argument("--strict", action="store_true", help="Exit 1 on any finding")
    ci.set_defaults(func=cloudinit_mod.run)

    # ansible — matches ansible.run(args): args.path, args.apply, args.strict
    an = sub.add_parser(
        "ansible", help="Patch Ansible playbooks (yum→dnf, python2→3, extras removal)"
    )
    an.add_argument("path", help="Playbook file or directory")
    an.add_argument(
        "--apply", action="store_true", help="Write changes (default dry-run)"
    )
    an.add_argument("--strict", action="store_true", help="Exit 1 on findings")
    an.set_defaults(func=ansible_mod.run)

    # runbook — matches runbook.run(args): args.kind, args.name, args.region, args.cluster, args.out
    rb = sub.add_parser(
        "runbook", help="Generate migration runbook for ASG/EKS/ECS/Beanstalk"
    )
    rb.add_argument(
        "--kind",
        required=True,
        choices=["asg", "eks", "ecs", "beanstalk"],
        help="Resource type",
    )
    rb.add_argument(
        "--name", help="Resource name (ASG / node group / task family / env)"
    )
    rb.add_argument("--region", default="us-east-1", help="AWS region")
    rb.add_argument("--cluster", help="Cluster name (for EKS/ECS)")
    rb.add_argument("--out", help="Output path (default: stdout)")
    rb.set_defaults(func=runbook_mod.run)

    return p


def _is_machine_output(args: argparse.Namespace) -> bool:
    fmt = getattr(args, "format", None)
    if fmt in ("json", "csv", "md", "markdown"):
        return True
    if getattr(args, "cmd", None) == "runbook" and not getattr(args, "out", None):
        return True
    return False


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv)

    if not getattr(args, "no_banner", False) and not _is_machine_output(args):
        sys.stderr.write(BANNER + "\n")

    try:
        return int(args.func(args) or 0)
    except KeyboardInterrupt:
        util.err("interrupted")
        return 130
    except FileNotFoundError as e:
        util.err(str(e))
        return 1
    except Exception as e:  # noqa: BLE001
        util.err(f"fatal: {e}")
        if os.environ.get("AL2023_GATE_DEBUG"):
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
