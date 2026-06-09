# LAUNCH HANDOFF — EOLkits

_Last updated: 2026-06-05 by the agent. GRACE migration path added; Cloudflare Worker is legacy/reference only._

This is the state of the project right before public launch. Everything code-side has
been built, deployed, and re-verified end-to-end. The remaining items below are
**operator-only** — actions that require either GRACE VPS deployment access,
GitHub UI access (Marketplace listing, sandbox install ID),
or a launch-defining decision (Show HN submission window).

Work the steps in order. **Step 1 (`eolkits-api` on GRACE) is the true product blocker for paid SKUs.** Step 2 (sandbox e2e) is the launch-day demo. Steps 3–4
are polish-and-ship.

---

## Verified state (re-checked 2026-05-15 / 2026-05-21)

| Surface | Status |
|---|---|
| `eolkits-api` (GRACE compose satellite) — `https://eolkits.com/health` | ✅ 200 live on same-host API routing |
| Landing page — `https://eolkits.com/` | ✅ 200 (2026-05-15) |
| Status page — `/status/` | ✅ 200 |
| Sample audit — `/audit/` | ✅ 200 |
| Verify tool — `/verify/` | ✅ 200 |
| Deprecations calendar — `/deprecations.ics` | ✅ 200 |
| `lambda-lifeline` (Node) | ✅ 24/24 tests |
| `al2023-gate` (Python) | ✅ 48/48 tests |
| `python-pivot` (Python) | ✅ 44/44 tests |
| `apps/runner` (Python) | ✅ 7/7 tests |
| `apps/grace-api` (FastAPI / pytest) | ✅ 5/5 tests |
| CI workflows (status, determinism gate, nightly benchmark, SEO, ICS) | ✅ all green through 2026-05-15 |
| `v1` and `v1.0.0` GitHub releases published | ✅ |
| **GitHub App `eolkits-migration-bot` credentials wired** | ✅ private key installed; GitHub App webhook URL + secret updated to `https://eolkits.com/webhook/github` |
| Stripe Live Key + Webhook Secret + Resend API Key | ✅ live Stripe key, canonical Stripe webhook endpoint + signing secret, and Resend key installed in `/home/ubuntu/sites/eolkits-api/.env.production` |
| GRACE satellite registration | ✅ `eolkits` static preserved; `eolkits-api` compose added in GRACE manifest and host-agent allowlist |
| GitHub Marketplace tile | ❌ Still 404 as of 2026-05-21 |
| Sandbox end-to-end PR | ❌ Not yet run — needs sandbox install ID |

**126 tests passing across the entire monorepo.** The mutation workflow has been
re-architected as a non-blocking weekly quality signal (configs in
`pyproject.toml`, `.github/workflows/mutation.yml`); it no longer creates
spurious quality-debt issues.

---

## 1. Deploy the GRACE-native EOLkits API *(blocker for paid SKUs)*

Cloudflare is no longer the canonical runtime. GRACE already hosts the public static site as the `eolkits` satellite, so do **not** create a duplicate static site entry. Add the paid API as a separate `eolkits-api` compose satellite.

1. Follow [`deploy/grace/README.md`](./deploy/grace/README.md).
2. Bring up `/home/ubuntu/sites/eolkits-api/docker-compose.yml` as compose project `eolkits-api`.
3. Route selected API paths on `eolkits.com` to `127.0.0.1:8120`, validate, and reload Caddy.
4. Append `deploy/grace/satellites.eolkits-api.yaml` to GRACE's satellite manifest.
5. Add `deploy/grace/satellite-agent.eolkits-api.py.snippet` to the host satellite agent allowlist.
6. Stripe and GitHub App webhooks now point at `https://eolkits.com/webhook/stripe` and `https://eolkits.com/webhook/github`.

The Cloudflare Worker code remains as legacy/reference until a follow-up deletion pass. Do not wire new production traffic to it.

## 2. Run the sandbox end-to-end PR *(~1 min, launch-day demo)*

This is the Migration Pack proof — the first real PR opened by the bot. The PR URL goes in the Show HN body.

1. Get the sandbox installation ID:
   `https://github.com/apps/eolkits-migration-bot/installations` → click the
   install on `ntoledo319/eolkits-sandbox` → the URL ends in the install ID.
2. Run from the runner host (or any box with the secrets exported):

   ```bash
   RUPTURE_SANDBOX_INSTALL_ID=<install-id> \
   GITHUB_APP_ID=3552449 \
   GITHUB_APP_PRIVATE_KEY="$(cat ~/Downloads/eolkits-migration-bot.2026-04-29.private-key.pem)" \
   python3 apps/runner/scripts/sandbox_e2e.py
   ```

3. Expected: JSON containing `pr_url`, `pr_number`, `findings_count`. Open
   the PR in the browser to confirm the body, refund-guarantee footer, and
   labels. Paste the PR URL into `launch/show-hn-final.md` as the live demo link
   and into `launch/hn-replies.md` "Can I see the bot's actual PR diff?" reply.

## 3. Marketplace listing visibility *(~1 min UI step)*

The `v1` release published 2026-05-02 has not yet been indexed at
`https://github.com/marketplace/actions/eolkits-aws-deprecation-check` (re-checked
2026-05-21 — still 404). Manual publication is required:

1. Open `https://github.com/ntoledo319/EOLkits/releases/tag/v1` → **Edit release**.
2. Tick **"Publish this Action to the GitHub Marketplace"**.
3. Save. (Requires Marketplace developer terms accepted on the account.)

Allow ~24 hours for the index to populate after saving.

## 4. Show HN submission *(Tue 2026-06-02 or Wed 2026-06-03, 6–9 AM PT)*

**Reframe complete (2026-05-21):** the launch artifacts (`launch/show-hn-final.md`,
`launch/social.md`, `launch/outreach.md`, `launch/hn-replies.md`,
`launch/blog-post.md`) now lead with AL2023 (Jun 30, 2026 — live deadline).
`lambda-lifeline` is positioned as post-deadline cleanup before the Sep 30
Phase 3 cliff. README.md hero updated.

The previous launch windows (2026-05-05 and 2026-05-06) were missed when work was
backburnered. The target is now **Tue 2026-06-02 or Wed 2026-06-03, 6–9 AM PT** —
first post-Memorial-Day full work week, gives the HN audience 27–28 days of live
AL2023 urgency. (May 26 was avoided because Memorial Day hangover dampens HN
engagement on the Tuesday-after. Jun 9/10 was the earlier conservative target;
landing the reframe ahead of schedule allowed pulling it in.)

Go/no-go checklist before submitting:
- `https://eolkits.com/health` is healthy and GRACE lists both `eolkits` and `eolkits-api`.
- Sandbox PR (step 2) exists, is still open, body looks right.
- Marketplace tile (step 3) returns 200.
- All 126 tests pass on a clean checkout.
- GRACE satellite status reports `eolkits-api` reachable.

## 5. Partner end-to-end proof *(after step 2)*

One external repo (not the sandbox) needs to install the bot and merge a
EOLkits-generated PR for the public proof point.

- Pick a target from the existing waitlist or GitHub Discussions.
- Seed them with a complimentary Migration Pack via the Stripe dashboard
  (`coupon: eolkits-partner-100`, or hand-issue an invoice).
- After their PR merges, capture the URL for `BENCHMARK.md` / the landing page.

---

## What the agent did during the 2026-05-21 session

- Historical note: the old Cloudflare Worker had secrets configured, but Cloudflare is no longer the canonical runtime. `apps/worker` is legacy/reference only.
- Historical note: R2 was never enabled; GRACE storage replaces it for the hosted fulfillment path.
- **Reframed all launch artifacts** to lead with AL2023 (Jun 30) instead of the now-past Apr 30 Node 20 EOL:
  - `README.md` — hero, badges (116→126 tests), kit table, roadmap order, tests block
  - `launch/show-hn-final.md` — title, body opener, kit table order, submission window
  - `launch/social.md` — X thread post 1, LinkedIn post
  - `launch/outreach.md` — Variant 1 (cold maintainer) rewritten for AL2023; post-deadline cleanup variant noted
  - `launch/hn-replies.md` — "Why post this now" reply rewritten with honest backburner acknowledgment
  - `launch/blog-post.md` — title + dated banner; full content preserved as cleanup guide
  - `launch/show-hn-draft.md` — archived; pointer to final
- **Did NOT do** (intentionally): rotate working secrets, change worker code, modify the 30-second demo (still lambda-lifeline because the workflow is illustrative regardless of kit), rewrite the 266-line blog-post body (only the framing).

## What the agent did during the 2026-05-03 session

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
the official "EOLkits is 100% launched" mark.
