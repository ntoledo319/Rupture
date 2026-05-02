"""
Package remap: AL2 yum package name → AL2023 dnf equivalent.

Sourced from:
 - AWS official AL2 → AL2023 comparison docs
 - amazon-linux-extras deprecation table
 - AL2023 release notes for replaced/renamed packages

Categories:
 - renamed       : same software, different package name
 - replaced_by   : different package providing same function
 - removed       : no AL2023 equivalent (action required)
 - extras_to_dnf : was in amazon-linux-extras, now in mainline dnf
 - same          : identical name, informational only
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class RemapEntry:
    al2_name: str
    al2023_name: Optional[str]
    category: str
    note: str = ""

    @property
    def action_required(self) -> bool:
        return self.category in ("removed", "replaced_by", "extras_to_dnf")


# Canonical table. Keep focused on the high-frequency packages that actually trip migrations.
REMAP_TABLE: Dict[str, RemapEntry] = {
    # amazon-linux-extras packages → now in main dnf repos
    "docker": RemapEntry(
        "docker",
        "docker",
        "extras_to_dnf",
        note="AL2 used `amazon-linux-extras install docker`. AL2023: `dnf install docker`.",
    ),
    "nginx1": RemapEntry(
        "nginx1",
        "nginx",
        "renamed",
        note="AL2 extras `nginx1` → AL2023 `nginx` (mainline).",
    ),
    "php8.1": RemapEntry(
        "php8.1",
        "php8.2",
        "replaced_by",
        note="AL2 extras had php up to 8.1. AL2023 ships php8.2 in mainline; php8.1 removed.",
    ),
    "php8.0": RemapEntry(
        "php8.0",
        "php8.2",
        "replaced_by",
        note="Upgrade to php8.2. php8.0 is EOL upstream and not in AL2023.",
    ),
    "php7.4": RemapEntry(
        "php7.4",
        "php8.2",
        "replaced_by",
        note="PHP 7.4 is upstream EOL. AL2023 has php8.2 only.",
    ),
    "python3.8": RemapEntry(
        "python3.8",
        "python3.11",
        "replaced_by",
        note="AL2023 default python is 3.11. 3.8 not available.",
    ),
    "python3.7": RemapEntry(
        "python3.7",
        "python3.11",
        "replaced_by",
        note="Upstream EOL. Migrate code to 3.11.",
    ),
    "postgresql14": RemapEntry(
        "postgresql14",
        "postgresql15",
        "replaced_by",
        note="AL2023 ships postgresql15 in mainline.",
    ),
    "postgresql13": RemapEntry(
        "postgresql13",
        "postgresql15",
        "replaced_by",
        note="PG 13 upstream EOL Nov 2025. AL2023 ships 15.",
    ),
    "mariadb10.5": RemapEntry(
        "mariadb10.5",
        "mariadb105",
        "renamed",
        note="Package naming convention changed; same software.",
    ),
    "redis6": RemapEntry(
        "redis6",
        "redis6",
        "extras_to_dnf",
        note="Now in mainline. Just `dnf install redis6`.",
    ),
    "memcached1.5": RemapEntry(
        "memcached1.5",
        "memcached",
        "renamed",
        note="AL2023: single `memcached` package.",
    ),
    "golang": RemapEntry(
        "golang", "golang", "extras_to_dnf", note="Use `dnf install golang` directly."
    ),
    "rust1": RemapEntry("rust1", "rust", "renamed", ""),
    "ruby3.0": RemapEntry(
        "ruby3.0",
        "ruby3.2",
        "replaced_by",
        note="AL2023 default is 3.2. Ruby 3.0 upstream EOL.",
    ),
    "ruby2.7": RemapEntry(
        "ruby2.7", "ruby3.2", "replaced_by", note="EOL. Migrate code."
    ),
    "nodejs14": RemapEntry(
        "nodejs14", "nodejs20", "replaced_by", note="Node 14 EOL. AL2023 ships 20 LTS."
    ),
    "nodejs12": RemapEntry("nodejs12", "nodejs20", "replaced_by", note="Node 12 EOL."),
    "tomcat9": RemapEntry(
        "tomcat9",
        None,
        "removed",
        note="No longer packaged. Install from upstream or use a different servlet container.",
    ),
    "corretto8": RemapEntry(
        "corretto8",
        "java-17-amazon-corretto",
        "replaced_by",
        note="AL2023 ships Corretto 17 by default. Corretto 8 via `dnf install java-1.8.0-amazon-corretto`.",
    ),
    "java-openjdk": RemapEntry(
        "java-openjdk",
        "java-17-amazon-corretto",
        "replaced_by",
        note="AL2023 replaces OpenJDK builds with Corretto.",
    ),
    # Removed/absent in AL2023
    "ntp": RemapEntry(
        "ntp",
        "chrony",
        "replaced_by",
        note="ntpd is removed. AL2023 uses chrony for time sync.",
    ),
    "python-pip": RemapEntry(
        "python-pip",
        "python3-pip",
        "renamed",
        note="Python 2 is gone. Use the Python 3 pip.",
    ),
    "python-virtualenv": RemapEntry(
        "python-virtualenv", "python3-virtualenv", "renamed"
    ),
    "yum-utils": RemapEntry(
        "yum-utils",
        "dnf-utils",
        "renamed",
        note="DNF replaces YUM. `yum-config-manager` is now `dnf config-manager`.",
    ),
    "yum-cron": RemapEntry(
        "yum-cron",
        "dnf-automatic",
        "replaced_by",
        note="Automatic updates now via dnf-automatic.timer.",
    ),
    "iptables-services": RemapEntry(
        "iptables-services",
        "iptables-legacy",
        "renamed",
        note="nftables is default. Install iptables-legacy for compat.",
    ),
    "screen": RemapEntry(
        "screen", "screen", "same", note="Still available via `dnf install screen`."
    ),
    "httpd24": RemapEntry(
        "httpd24",
        "httpd",
        "renamed",
        note="Apache 2.4 is the default; no version suffix.",
    ),
    "vsftpd": RemapEntry("vsftpd", "vsftpd", "same"),
    "sendmail": RemapEntry("sendmail", "sendmail", "same"),
    "postfix": RemapEntry("postfix", "postfix", "same"),
    "gcc72": RemapEntry(
        "gcc72", "gcc", "replaced_by", note="AL2023 ships gcc 11 by default."
    ),
    "gcc64": RemapEntry("gcc64", "gcc", "replaced_by", ""),
    "vim-minimal": RemapEntry("vim-minimal", "vim-minimal", "same"),
    "bind-utils": RemapEntry("bind-utils", "bind-utils", "same"),
    "telnet": RemapEntry("telnet", "telnet", "same"),
    "mysql": RemapEntry(
        "mysql",
        "mariadb105",
        "replaced_by",
        note="MySQL client repackaged as mariadb. For MySQL server, use the upstream repo.",
    ),
    "mysql-server": RemapEntry("mysql-server", "mariadb105-server", "replaced_by", ""),
    # Kernel / init
    "kernel": RemapEntry(
        "kernel",
        "kernel",
        "same",
        note="Different major version (AL2: 5.10/5.15 LTS; AL2023: 6.1+).",
    ),
    "systemd": RemapEntry(
        "systemd",
        "systemd",
        "same",
        note="AL2023 has a newer systemd. Check unit file compatibility.",
    ),
    # Common libs whose ABI or path changed
    "openssl": RemapEntry(
        "openssl",
        "openssl",
        "same",
        note="AL2: OpenSSL 1.0.2. AL2023: OpenSSL 3. Breaking ABI change — rebuild native code.",
    ),
    "openssl-devel": RemapEntry("openssl-devel", "openssl-devel", "same", ""),
    "curl": RemapEntry(
        "curl",
        "curl-minimal",
        "renamed",
        note="AL2023 splits curl into minimal by default. `dnf swap curl-minimal curl` for full.",
    ),
}


def lookup(pkg: str) -> Optional[RemapEntry]:
    return REMAP_TABLE.get(pkg)


def remap_package_list(packages: List[str]) -> List[RemapEntry]:
    """Given a list of AL2 package names, return a remap entry per package (best-effort)."""
    out: List[RemapEntry] = []
    for p in packages:
        entry = REMAP_TABLE.get(p)
        if entry:
            out.append(entry)
        else:
            # Unknown package — assume same name, informational only
            out.append(
                RemapEntry(
                    al2_name=p,
                    al2023_name=p,
                    category="unknown",
                    note="Not in our curated remap table; verify it exists in AL2023.",
                )
            )
    return out


def categorize(entries: List[RemapEntry]) -> Dict[str, List[RemapEntry]]:
    buckets: Dict[str, List[RemapEntry]] = {}
    for e in entries:
        buckets.setdefault(e.category, []).append(e)
    return buckets


# -------- CLI entrypoint --------


def _collect_packages(args) -> List[str]:
    pkgs: List[str] = []
    if getattr(args, "packages", None):
        pkgs.extend(args.packages)
    if getattr(args, "file", None):
        import os

        if not os.path.isfile(args.file):
            raise FileNotFoundError(f"package list not found: {args.file}")
        with open(args.file, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                pkgs.append(line)
    # de-dup preserving order
    seen = set()
    out = []
    for p in pkgs:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _render_table(entries: List[RemapEntry]) -> str:
    # column widths
    c1 = max(len("AL2 PACKAGE"), max((len(e.al2_name) for e in entries), default=0))
    c2 = max(
        len("AL2023 EQUIVALENT"),
        max((len(e.al2023_name or "—") for e in entries), default=0),
    )
    c3 = max(len("CATEGORY"), max((len(e.category) for e in entries), default=0))
    header = (
        f"{'AL2 PACKAGE':<{c1}}  {'AL2023 EQUIVALENT':<{c2}}  {'CATEGORY':<{c3}}  NOTE"
    )
    sep = "-" * len(header)
    lines = [header, sep]
    for e in entries:
        marker = "!" if e.action_required else " "
        lines.append(
            f"{e.al2_name:<{c1}}  {(e.al2023_name or '—'):<{c2}}  {e.category:<{c3}} {marker} {e.note}"
        )
    return "\n".join(lines)


def _render_markdown(entries: List[RemapEntry]) -> str:
    lines = [
        "| AL2 package | AL2023 equivalent | Category | Action | Note |",
        "|-------------|-------------------|----------|--------|------|",
    ]
    for e in entries:
        act = "⚠️" if e.action_required else "✓"
        note = e.note.replace("|", "\\|")
        lines.append(
            f"| `{e.al2_name}` | `{e.al2023_name or '—'}` | {e.category} | {act} | {note} |"
        )
    return "\n".join(lines)


def _render_json(entries: List[RemapEntry]) -> str:
    import json

    payload = [
        {
            "al2_name": e.al2_name,
            "al2023_name": e.al2023_name,
            "category": e.category,
            "action_required": e.action_required,
            "note": e.note,
        }
        for e in entries
    ]
    return json.dumps(payload, indent=2)


def run(args) -> int:
    from . import util

    try:
        packages = _collect_packages(args)
    except FileNotFoundError as e:
        util.err(str(e))
        return 1

    if not packages:
        util.err("no packages specified (pass package names or --file)")
        return 1

    entries = remap_package_list(packages)
    fmt = getattr(args, "format", "table")

    if fmt == "json":
        print(_render_json(entries))
    elif fmt == "md":
        print(_render_markdown(entries))
    else:
        print(_render_table(entries))

    # Exit code: 0 if everything known/same, 1 if anything removed (hard block)
    hard = any(e.category == "removed" for e in entries)
    return 1 if hard else 0
