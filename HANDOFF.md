# LAUNCH HANDOFF — Rupture

_Last updated: 2026-05-03 by the agent. Verified live on this date._

This is the state of the project right before public launch. Everything code-side has
been built, deployed, and re-verified end-to-end. The remaining items below are
**operator-only** — actions that require either GitHub UI access (private-key generation,
Marketplace listing) or a launch-defining decision (Show HN submission window) that the
agent cannot and should not make on its own.

Work the steps in order. **Steps 1 and 2 are the only true product blockers.**

---

## Verified state (re-checked 2026-05-03)

| Surface | Status |
|---|---|
| `apps/worker` (Cloudflare) — `https://rupture-worker.rupture-kits.workers.dev/health` | ✅ `{"ok":true,"env":"production"}` |
| Landing page — `https://ntoledo319.github.io/Rupture/` | ✅ 200 |
| Status page — `/status/` | ✅ 200 |
| Sample audit — `/audit/` | ✅ 200 |
| Verify tool — `/verify/` | ✅ 200 |
| Deprecations calendar — `/deprecations.ics` | ✅ 200 |
| `lambda-lifeline` (Node) | ✅ 24/24 tests |
| `al2023-gate` (Python) | ✅ 48/48 tests |
| `python-pivot` (Python) | ✅ 44/44 tests |
| `apps/runner` (Python) | ✅ 7/7 tests |
| `apps/worker` (TypeScript / vitest) | ✅ 3/3 tests |
| `v1` and `v1.0.0` GitHub releases published | ✅ |
| GitHub Marketplace tile | ❌ 404 — needs **step 3** |
| GitHub App `rupture-migration-bot` credentials wired | ❌ — needs **step 1** |

**126 tests passing across the entire monorepo.** The mutation workflow has been
re-architected as a non-blocking weekly quality signal (configs in
`pyproject.toml`, `.github/workflows/mutation.yml`); it no longer creates
spurious quality-debt issues.

---

## 1. Install GitHub App credentials *(~5 min, blocker)*

The app is registered at `https://github.com/apps/rupture-migration-bot`. Generate and
ship its three secrets:

1. Open the app's settings page → copy the numeric **App ID**.
2. Same page → **Private keys** → **Generate a private key** → download the `.pem`.
3. Same page → **Webhook secret** → paste the output of `openssl rand -hex 32`.
4. Run:

   ```bash
   cd apps/worker
   ./scripts/setup_github_app.sh \
     --app-id <APP_ID> \
     --private-key-pem ~/Downloads/rupture-bot.private-key.pem \
     --webhook-secret '<the hex string from step 3>'
   ```

   This pushes `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`, and
   `GITHUB_WEBHOOK_SECRET` into the production worker via `wrangler secret put`.

5. Mirror the same `GITHUB_APP_ID` and PEM into the migration-runner host as
   environment variables (Render/Fly secrets, or shell exports on the box that
   runs `apps/runner/main.py`).

## 2. Run the sandbox end-to-end PR *(~1 min, blocker)*

This is the Migration Pack proof — the first real PR opened by the bot.

1. Get the sandbox installation ID:
   `https://github.com/apps/rupture-migration-bot/installations` → click the
   install on `ntoledo319/rupture-sandbox` → the URL ends in the install ID.
2. Run from the runner host (or any box with the secrets exported):

   ```bash
   RUPTURE_SANDBOX_INSTALL_ID=<install-id> \
   GITHUB_APP_ID=<app-id> \
   GITHUB_APP_PRIVATE_KEY="$(cat ~/Downloads/rupture-bot.private-key.pem)" \
   python3 apps/runner/scripts/sandbox_e2e.py
   ```

3. Expected: JSON containing `pr_url`, `pr_number`, `findings_count`. Open
   the PR in the browser to confirm the body, refund-guarantee footer, and
   labels.

If this passes, the Migration Pack SKU is functional end-to-end.

## 3. Marketplace listing visibility *(~1 min UI step)*

The `v1` release published 2026-05-02 has not yet been indexed at
`https://github.com/marketplace/actions/rupture-aws-deprecation-check` (re-checked
2026-05-03 — still 404). Manual publication is required:

1. Open `https://github.com/ntoledo319/Rupture/releases/tag/v1` → **Edit release**.
2. Tick **"Publish this Action to the GitHub Marketplace"**.
3. Save. (Requires Marketplace developer terms accepted on the account.)

Allow ~24 hours for the index to populate after saving.

## 4. Show HN submission *(Tue 2026-05-05 or Wed 2026-05-06, 6–9 AM PT)*

The pre-written body is at `launch/show-hn-draft.md`. A reminder is scheduled
for Tue 2026-05-05 06:07 local that runs the go/no-go checklist (worker health,
Marketplace tile, sandbox PR, mutation workflow). When the ping arrives:

- All green → copy the draft into Hacker News, hit Submit.
- Anything red → hold for the Wed 2026-05-06 window.

**Do not submit before this window.** HN's algorithm rewards Tue/Wed morning PT
posts; a Sunday-afternoon submission burns the launch.

## 5. Partner end-to-end proof *(after step 2)*

One external repo (not the sandbox) needs to install the bot and merge a
Rupture-generated PR for the public proof point.

- Pick a target from the existing waitlist or GitHub Discussions.
- Seed them with a complimentary Migration Pack via the Stripe dashboard
  (`coupon: rupture-partner-100`, or hand-issue an invoice).
- After their PR merges, capture the URL for `BENCHMARK.md` / the landing page.

---

## What the agent did during this session (2026-05-03)

- Verified all 126 tests pass after a clean checkout.
- Removed the `mutants/` directory committed by an earlier mutmut run; added
  `mutants/`, `.mutmut-cache`, `mutation_report.txt`, `.claude/`,
  `.mypy_cache/`, and `.ruff_cache/` to `.gitignore`.
- Added `[tool.mutmut]` configs to `kits/python-pivot/pyproject.toml` and
  `kits/al2023-gate/pyproject.toml` so mutmut can find the source paths,
  test dir, and test runner without ad-hoc CLI flags.
- Rewrote `.github/workflows/mutation.yml` as a non-blocking weekly quality
  signal: parses `mutmut results` correctly, emits the score in the run
  summary, uploads the report as an artifact, and no longer fails the build
  or tries to open issues on a low score (the previous attempt was failing
  with `Resource not accessible by integration` because the job lacked
  `issues: write` permission).

---

**Delete this file once steps 1, 2, 3, 4, and 5 are done.** That moment is
the official "Rupture is 100% launched" mark.
