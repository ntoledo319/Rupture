# Launch Readiness — Rupture (snapshot 2026-05-02)

Single source of truth for what's needed to flip the project to **100% launched**.

## Status legend
- 🟢 done
- 🟡 ready, requires one external action
- 🔴 work pending

---

## 1. Code & infrastructure

| Area | Status | Notes |
|---|---|---|
| Cloudflare worker (router, webhooks, queue) | 🟢 | `https://rupture-worker.rupture-kits.workers.dev/health` returns `ok` |
| Stripe live checkout | 🟢 | `STRIPE_KEY` + webhook endpoint set |
| Resend email | 🟢 | `RESEND_API_KEY` set |
| KV / R2 / Queues / DLQ | 🟢 | Bindings live, `/status` reports healthy |
| Migration runner — code path | 🟢 | `apps/runner/migration_pr.py` now does real install-token clone, kit scan/apply, branch push, and PR open via the GitHub API |
| Sandbox E2E script | 🟢 | `apps/runner/scripts/sandbox_e2e.py` runs the full flow against `ntoledo319/rupture-sandbox` |
| GitHub Action root + `v1` tag | 🟢 | Both present; release on `v1` exists |
| GitHub Action Marketplace listing | 🟡 | `v1` release published 2026-05-02; awaiting GitHub indexing of `https://github.com/marketplace/actions/rupture-aws-deprecation-check` |

## 2. Credentials (operator-only, not generatable from CLI)

| Item | Status | Action |
|---|---|---|
| `GITHUB_APP_ID` | 🔴 | App exists at `https://github.com/apps/rupture-migration-bot`; copy the App ID from the settings page |
| `GITHUB_APP_PRIVATE_KEY` | 🔴 | Generate from the App settings → "Private keys" → Generate, download `.pem` |
| `GITHUB_WEBHOOK_SECRET` | 🔴 | Generate `openssl rand -hex 32`; paste into App settings → Webhook secret |
| Apply all three | 🔴 | One command: `apps/worker/scripts/setup_github_app.sh --app-id … --private-key-pem … --webhook-secret …` |

After these land, run the sandbox E2E:
```bash
RUPTURE_SANDBOX_INSTALL_ID=<install-id-from-app-installations-page> \
GITHUB_APP_ID=<id> \
GITHUB_APP_PRIVATE_KEY="$(cat rupture-bot.private-key.pem)" \
python3 apps/runner/scripts/sandbox_e2e.py
```
Expected: a real PR on `ntoledo319/rupture-sandbox`, JSON output with `pr_url`, `pr_number`, `findings_count`.

## 3. Quality gates

| Gate | Status | Notes |
|---|---|---|
| Test suite (116 tests across 3 kits) | 🟢 | Passing on `main` |
| Determinism CI gate | 🟢 | Workflow green |
| Property-based tests | 🟢 | Workflow green |
| Mutation score ≥ 80% | 🟡 | Triggered 2026-05-02; check `gh run list -R ntoledo319/Rupture --workflow mutation.yml --limit 1` |
| Reproducible release | 🟢 | `v1.0.0` published with SBOMs + sigs |
| Runner unit tests for migration flow | 🟢 | `apps/runner/test/test_migration_pr.py` |

## 4. Distribution

| Channel | Status | Notes |
|---|---|---|
| GitHub Pages landing | 🟢 | `https://ntoledo319.github.io/Rupture` |
| VS Code extension `rupture.rupture-vscode` | 🟢 | Marketplace v1.0.0 |
| GitHub Action `ntoledo319/Rupture@v1` | 🟡 | Tag + release exist; Marketplace tile pending GitHub indexing |
| Show HN post | 🔴 | Hold for **Tue 2026-05-05** or **Wed 2026-05-06**, 6–9 AM PT |
| SEO blog post (Dev.to / Medium) | 🔴 | Draft ready in `launch/blog-post.md` |
| Thread replies (SO / GH / re:Post) | 🔴 | Templates in `launch/thread-answers.md` |

## 5. Partner / external proof

| Item | Status | Notes |
|---|---|---|
| Public benchmark | 🟢 | `BENCHMARK.md` covers 12 public repos, no warnings |
| Partner end-to-end proof | 🔴 | Needs at least one external repo (not the sandbox) installing the App and merging a Rupture PR — unblocked once §2 credentials land |

---

## What's actually left (in execution order)

1. **Operator: install GitHub App credentials** — register/copy from `/pack/install`, then run `apps/worker/scripts/setup_github_app.sh`. ETA: 5 min.
2. **Operator: run sandbox E2E** — `apps/runner/scripts/sandbox_e2e.py`. ETA: 1 min, produces real PR.
3. **Operator: confirm Marketplace listing indexed** — visit `https://github.com/marketplace/actions/rupture-aws-deprecation-check`. If still 404 after 24h of the `v1` release, "Publish to Marketplace" toggle on the release page.
4. **Mutation score** — running now, will report on the next sweep. If <80%, the workflow opens a quality-debt issue.
5. **Show HN** — submit on 2026-05-05 (preferred) or 2026-05-06.
6. **Partner E2E** — pick a target repo from the existing waitlist / Discussions and seed a paid Migration Pack as proof.

Steps 1–2 are the only true blockers for "Migration Pack actually works in prod." The rest are visibility / proof items, not gates on the system functioning.
