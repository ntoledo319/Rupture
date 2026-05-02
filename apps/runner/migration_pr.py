"""
Migration PR creation — opens real PRs on user repositories.

Authenticates as a GitHub App installation, clones the target repo, runs the
appropriate Rupture kit (lambda-lifeline / al2023-gate / python-pivot), commits
the codemod output to a new branch, and opens a PR with refund-guarantee body.

Required environment:
  GITHUB_APP_ID            - numeric App ID
  GITHUB_APP_PRIVATE_KEY   - PEM contents (PKCS#1 or PKCS#8)
  RUPTURE_GIT_USER_EMAIL   - optional, default rupture-bot@users.noreply.github.com
  RUPTURE_GIT_USER_NAME    - optional, default "rupture-bot"
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import tempfile
import time
from typing import Dict, List, Optional

import requests

try:
    import jwt  # PyJWT
except ImportError:  # pragma: no cover - jwt is added in requirements.txt
    jwt = None  # type: ignore


GITHUB_API = "https://api.github.com"
DEFAULT_GIT_USER_EMAIL = "rupture-bot@users.noreply.github.com"
DEFAULT_GIT_USER_NAME = "rupture-bot"
KIT_SCAN_TIMEOUT_SECS = 600


def create_migration_pr(
    repo: str,
    email: str,
    installation_id: str,
) -> Dict:
    """Create a migration PR on the specified repository."""
    if not repo or "/" not in repo:
        raise ValueError(f"Invalid repo identifier: {repo!r}")

    token = mint_installation_token(str(installation_id))

    if check_no_rupture(repo, token):
        raise ValueError(f"Repository {repo} has opted out via .no-rupture file")

    default_branch = get_default_branch(repo, token)
    kit = detect_kit_for_repo(repo, token)

    with tempfile.TemporaryDirectory() as workdir:
        clone_repo(repo, token, workdir, default_branch)

        findings = run_kit_analysis(kit, workdir)
        if not findings:
            raise ValueError("No applicable deprecations found in repository")

        short_hash = os.urandom(4).hex()
        branch_name = f"rupture/migrate-{kit}-{short_hash}"

        create_branch(workdir, branch_name)
        apply_codemods(kit, workdir, findings)

        if not has_changes(workdir):
            raise ValueError("Kit ran but produced no diff; nothing to commit")

        pr_title = f"[Rupture] Migrate {kit.replace('-', ' ')} deprecated patterns"
        pr_body = generate_pr_body(kit, findings, email)

        configure_git_identity(workdir)
        commit_and_push(workdir, branch_name, kit, repo, token)

        pr_info = open_pull_request(
            repo=repo,
            head=branch_name,
            base=default_branch,
            title=pr_title,
            body=pr_body,
            token=token,
        )
        add_refund_label(repo, pr_info["pr_number"], token)

        return {
            "pr_url": pr_info["pr_url"],
            "pr_number": pr_info["pr_number"],
            "branch": branch_name,
            "kit": kit,
            "findings_count": len(findings),
        }


# -------- GitHub App auth --------------------------------------------------- #


def _generate_jwt() -> str:
    if jwt is None:
        raise RuntimeError("PyJWT is required; add 'PyJWT[crypto]' to requirements.txt")

    app_id = os.environ.get("GITHUB_APP_ID")
    private_key = os.environ.get("GITHUB_APP_PRIVATE_KEY")
    if not app_id or not private_key:
        raise RuntimeError(
            "GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY must be set in the runner environment"
        )

    private_key = private_key.replace("\\n", "\n")
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + 9 * 60,
        "iss": app_id,
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


def mint_installation_token(installation_id: str) -> str:
    """Exchange the App JWT for an installation access token."""
    app_jwt = _generate_jwt()
    resp = requests.post(
        f"{GITHUB_API}/app/installations/{installation_id}/access_tokens",
        headers={
            "Authorization": f"Bearer {app_jwt}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=30,
    )
    if resp.status_code >= 300:
        raise RuntimeError(
            f"Failed to mint installation token ({resp.status_code}): {resp.text}"
        )
    return resp.json()["token"]


def _gh_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "rupture-runner",
    }


# -------- Repo discovery ---------------------------------------------------- #


def get_default_branch(repo: str, token: str) -> str:
    resp = requests.get(
        f"{GITHUB_API}/repos/{repo}", headers=_gh_headers(token), timeout=15
    )
    resp.raise_for_status()
    return resp.json().get("default_branch", "main")


def check_no_rupture(repo: str, token: str) -> bool:
    """Look for a `.no-rupture` opt-out file at the repo root."""
    resp = requests.get(
        f"{GITHUB_API}/repos/{repo}/contents/.no-rupture",
        headers=_gh_headers(token),
        timeout=15,
    )
    return resp.status_code == 200


def detect_kit_for_repo(repo: str, token: str) -> str:
    """Pick a kit based on repo contents.

    Heuristic order:
      1. SAM/CDK/Terraform with nodejs20.x → lambda-lifeline
      2. Dockerfile/AMI references to AL2 → al2023-gate
      3. Python 3.8/3.9 references → python-pivot
      4. Default → lambda-lifeline (safest mechanical codemod set)
    """
    override = os.environ.get("RUPTURE_KIT")
    if override:
        return override

    def _has(path: str, needle: Optional[str] = None) -> bool:
        resp = requests.get(
            f"{GITHUB_API}/repos/{repo}/contents/{path}",
            headers=_gh_headers(token),
            timeout=15,
        )
        if resp.status_code != 200:
            return False
        if needle is None:
            return True
        body = resp.json()
        if isinstance(body, list):
            return False
        content = body.get("content", "")
        try:
            decoded = base64.b64decode(content).decode("utf-8", errors="ignore")
        except Exception:
            return False
        return needle in decoded

    if _has("template.yaml", "nodejs20") or _has("samconfig.toml"):
        return "lambda-lifeline"
    if _has("Dockerfile", "amazonlinux:2"):
        return "al2023-gate"
    if _has("requirements.txt", "python_requires=") or _has("pyproject.toml", "python = \"3.8"):
        return "python-pivot"
    return "lambda-lifeline"


# -------- Git operations ---------------------------------------------------- #


def configure_git_identity(workdir: str) -> None:
    email = os.environ.get("RUPTURE_GIT_USER_EMAIL", DEFAULT_GIT_USER_EMAIL)
    name = os.environ.get("RUPTURE_GIT_USER_NAME", DEFAULT_GIT_USER_NAME)
    subprocess.run(
        ["git", "config", "user.email", email], cwd=workdir, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", name], cwd=workdir, check=True
    )


def clone_repo(repo: str, token: str, workdir: str, branch: str) -> None:
    """Clone using HTTPS with the installation token as the password."""
    url = f"https://x-access-token:{token}@github.com/{repo}.git"
    subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", branch, url, workdir],
        check=True,
        capture_output=True,
    )


def has_changes(workdir: str) -> bool:
    out = subprocess.run(
        ["git", "status", "--porcelain"], cwd=workdir, capture_output=True, text=True, check=True
    )
    return bool(out.stdout.strip())


def create_branch(workdir: str, branch_name: str) -> None:
    subprocess.run(
        ["git", "checkout", "-b", branch_name],
        cwd=workdir,
        check=True,
        capture_output=True,
    )


def commit_and_push(
    workdir: str, branch_name: str, kit: str, repo: str, token: str
) -> None:
    subprocess.run(["git", "add", "-A"], cwd=workdir, check=True)
    subprocess.run(
        [
            "git",
            "commit",
            "-m",
            f"[rupture] apply {kit} migration\n\nGenerated by rupture-bot. See PR body for details.",
        ],
        cwd=workdir,
        check=True,
    )
    push_url = f"https://x-access-token:{token}@github.com/{repo}.git"
    subprocess.run(
        ["git", "push", push_url, f"HEAD:refs/heads/{branch_name}"],
        cwd=workdir,
        check=True,
        capture_output=True,
    )


# -------- Kit invocation ---------------------------------------------------- #


def _kit_command(kit: str, action: str, workdir: str) -> List[str]:
    if kit == "lambda-lifeline":
        # CLI is installed in the runner image; it understands `scan --json` and `codemod --apply`.
        if action == "scan":
            return ["lambda-lifeline", "scan", "--path", workdir, "--json"]
        return ["lambda-lifeline", "codemod", "--path", workdir, "--apply"]
    if kit == "al2023-gate":
        if action == "scan":
            return ["al2023-gate", "scan", "--path", workdir, "--json"]
        return ["al2023-gate", "patch", "--path", workdir, "--apply"]
    if kit == "python-pivot":
        if action == "scan":
            return ["python-pivot", "scan", "--path", workdir, "--json"]
        return ["python-pivot", "codemod", "--path", workdir, "--apply"]
    raise ValueError(f"Unknown kit: {kit}")


def run_kit_analysis(kit: str, workdir: str) -> List[Dict]:
    cmd = _kit_command(kit, "scan", workdir)
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=KIT_SCAN_TIMEOUT_SECS
    )
    if proc.returncode != 0 and not proc.stdout.strip():
        raise RuntimeError(
            f"Kit scan failed ({kit}, exit {proc.returncode}): {proc.stderr.strip()[:500]}"
        )
    try:
        parsed = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, dict):
        return parsed.get("findings", [])
    return parsed if isinstance(parsed, list) else []


def apply_codemods(kit: str, workdir: str, findings: List[Dict]) -> None:
    cmd = _kit_command(kit, "apply", workdir)
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=KIT_SCAN_TIMEOUT_SECS
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Kit apply failed ({kit}, exit {proc.returncode}): {proc.stderr.strip()[:500]}"
        )


# -------- PR body & API ----------------------------------------------------- #


def generate_pr_body(kit: str, findings: List[Dict], email: str) -> str:
    body = f"""## Rupture Automated Migration

This PR was generated by [Rupture](https://ntoledo319.github.io/Rupture) to migrate deprecated AWS runtime patterns.

### Kit Used
**{kit}** — Automated codemods and IaC patches

### Findings
| Type | File | Description |
|------|------|-------------|
"""
    for finding in findings:
        body += (
            f"| {finding.get('type', 'finding')} "
            f"| {finding.get('file', 'unknown')} "
            f"| Line {finding.get('line', 'N/A')} |\n"
        )

    body += f"""
### What Changed
- Applied mechanical codemods for safe transformations
- Updated IaC templates to new runtime versions
- Added canary deployment configuration
- Included rollback script

### Next Steps
1. Review the changes in the Files changed tab
2. Run your test suite
3. Deploy using the included canary plan
4. Monitor CloudWatch alarms during cutover

### Refund Guarantee
If CI fails on this PR within 7 days, your purchase will be automatically refunded. No human intervention required.

To override this (e.g., if failure is unrelated), add the `override:ci-failure` label.

---
*This PR was generated for {email}*
*Report issues: https://github.com/ntoledo319/Rupture/issues*
"""
    return body


def open_pull_request(
    repo: str,
    head: str,
    base: str,
    title: str,
    body: str,
    token: str,
) -> Dict:
    resp = requests.post(
        f"{GITHUB_API}/repos/{repo}/pulls",
        headers=_gh_headers(token),
        json={"title": title, "head": head, "base": base, "body": body, "maintainer_can_modify": True},
        timeout=30,
    )
    if resp.status_code >= 300:
        raise RuntimeError(f"Failed to open PR ({resp.status_code}): {resp.text}")
    pr = resp.json()
    return {"pr_url": pr["html_url"], "pr_number": pr["number"]}


def add_refund_label(repo: str, pr_number: int, token: str) -> None:
    """Best-effort label add; don't fail the job if labeling fails."""
    try:
        requests.post(
            f"{GITHUB_API}/repos/{repo}/issues/{pr_number}/labels",
            headers=_gh_headers(token),
            json={"labels": ["rupture", "migration"]},
            timeout=15,
        )
    except Exception:
        pass


def extract_pr_number(pr_url: str) -> int:
    return int(pr_url.rstrip("/").split("/")[-1])
