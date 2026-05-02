# FINAL HANDOFF — Rupture (2026-05-02)

Everything code-side is shipped. What's left below is **operator-only**: things the agent cannot do without your hands on a browser, a credential download, or a launch-day post.

Work in this order. Steps 1–2 are the only true product blockers.

---

## 1. Install GitHub App credentials  *(~5 min)*

The app is registered at `https://github.com/apps/rupture-migration-bot`. Generate and ship its three secrets:

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

   This pushes `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`, and `GITHUB_WEBHOOK_SECRET` into the production worker via `wrangler secret put`.

5. Mirror the same `GITHUB_APP_ID` and PEM into the migration-runner host as environment variables (Render/Fly secrets, or shell exports on the box that runs `apps/runner/main.py`).

## 2. Run the sandbox end-to-end PR  *(~1 min)*

This is the Migration Pack proof — first real PR opened by the bot.

1. Get the sandbox installation ID: `https://github.com/apps/rupture-migration-bot/installations` → click the install on `ntoledo319/rupture-sandbox` → the URL ends in the install ID.
2. Run from the runner host (or any box with the secrets exported):

   ```bash
   RUPTURE_SANDBOX_INSTALL_ID=<install-id> \
   GITHUB_APP_ID=<app-id> \
   GITHUB_APP_PRIVATE_KEY="$(cat ~/Downloads/rupture-bot.private-key.pem)" \
   python3 apps/runner/scripts/sandbox_e2e.py
   ```

3. Expected: JSON containing `pr_url`, `pr_number`, `findings_count`. Open the PR in your browser to confirm the body, refund-guarantee footer, and labels.

If this passes, the Migration Pack SKU is functional end-to-end.

## 3. Marketplace listing visibility  *(~24 h passive, then 1-min UI step if needed)*

A `v1` release was published on 2026-05-02 to drive Marketplace indexing.

- Check `https://github.com/marketplace/actions/rupture-aws-deprecation-check` after ~24 h.
- If still 404: open `https://github.com/ntoledo319/Rupture/releases/tag/v1` → **Edit release** → tick **"Publish this Action to the GitHub Marketplace"** → save. (Requires you to have accepted the Marketplace developer terms once.)

## 4. Mutation score ≥ 80%  *(passive, then triage if it fails)*

A run was dispatched 2026-05-02. Check it:

```bash
gh run list -R ntoledo319/Rupture --workflow mutation.yml --limit 1 \
  --json status,conclusion,url
```

- Conclusion `success` → done; report files are in the workflow artifacts.
- Conclusion `failure` → score is below 80% on at least one kit. The workflow's `mutation_report.txt` artifact lists surviving mutants; add tests in the relevant `kits/<kit>/test/` directory until the next dispatch passes.

## 5. Show HN submission  *(Tue 2026-05-05 or Wed 2026-05-06, 6–9 AM PT)*

A reminder is scheduled for Tue 2026-05-05 06:07 local that runs the go/no-go checklist (worker health, Marketplace tile, sandbox PR, mutation score). When you get the ping:

- All green → copy `launch/show-hn-draft.md` into Hacker News.
- Anything red → hold for the Wed 2026-05-06 window.

## 6. Partner end-to-end proof  *(after step 2)*

One external repo (not the sandbox) needs to install the bot and merge a Rupture-generated PR for the public proof point.

- Pick a target from the existing waitlist or GitHub Discussions.
- Seed them with a complimentary Migration Pack via the Stripe dashboard (`coupon: rupture-partner-100`, or hand-issue an invoice).
- After their PR merges, capture the URL for `BENCHMARK.md` / the landing page.

---

## What the agent already did (so you don't have to revisit it)

- `apps/runner/migration_pr.py` — real installation-token clone, kit dispatch (`lambda-lifeline` / `al2023-gate` / `python-pivot`), branch push, PR open via the GitHub REST API. PyJWT-signed JWTs.
- `apps/runner/scripts/sandbox_e2e.py` — one-shot smoke for the sandbox repo (used in step 2).
- `apps/runner/test/test_migration_pr.py` — 5 unit tests, passing.
- `apps/worker/scripts/setup_github_app.sh` — wraps `wrangler secret put` for the three secrets (used in step 1).
- `v1` GitHub release published — drives Marketplace indexing for step 3.
- Mutation workflow dispatched — feeds step 4.
- Show HN reminder scheduled for 2026-05-05 06:07 local — feeds step 5.
- Commit `c206391` pushed to `main` (now superseded by the cleanup commit you're reading from).

---

**Delete this file once steps 1–6 are done.** That moment is the official "Rupture is 100% launched" mark.
