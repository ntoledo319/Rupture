# Operator Decisions — Rupture Launch

> Source: `updateplan.md` §2. Current state after the May 2, 2026 launch-hardening pass.

---

## [DECISION-1] GitHub organization for hosting
- **Status:** RESOLVED — default applied
- **Decision:** `ntoledo319` (existing personal account)
- **Repo:** https://github.com/ntoledo319/Rupture

## [DECISION-2] Public-facing URL for launch
- **Status:** RESOLVED — default applied
- **Decision:** GitHub Pages at `https://ntoledo319.github.io/Rupture`
- **Custom domain:** deferred until first $50 of revenue clears (per $0-seed rule)

## [DECISION-3] Stripe account
- **Status:** RESOLVED — live mode active
- **Worker secret:** `STRIPE_KEY` is set in the production Cloudflare Worker.
- **Webhook:** live Stripe webhook endpoint registered for `https://rupture-worker.rupture-kits.workers.dev/webhook/stripe`.
- **Smoke check:** audit checkout returns a live Stripe Checkout redirect without charging.

## [DECISION-4] Cloudflare account
- **Status:** RESOLVED — production Worker deployed
- **Account:** `8386730baf2dc6008a63c5bfd92c6f49`
- **Worker:** `https://rupture-worker.rupture-kits.workers.dev`
- **Bindings:** KV, R2 (`rupture-uploads`), Queues (`rupture-jobs`, `rupture-jobs-dlq`), and Workers AI are configured.
- **Health:** `/status` reports healthy for KV, R2, Queue, and Stripe.

## [DECISION-5] Resend (transactional email)
- **Status:** RESOLVED — default applied
- **Decision:** Resend free tier (3,000 emails/month, 100/day)
- **Worker secret:** `RESEND_API_KEY` is set in the production Cloudflare Worker.

## [DECISION-6] GitHub App registration
- **Status:** PARTIALLY RESOLVED
- **Public app:** https://github.com/apps/rupture-migration-bot exists.
- **Sandbox repo:** `ntoledo319/rupture-sandbox` exists.
- **Install endpoint:** `https://rupture-worker.rupture-kits.workers.dev/pack/install` returns a manifest with webhook `https://rupture-worker.rupture-kits.workers.dev/webhook/github`.
- **Remaining:** install `GITHUB_APP_PRIVATE_KEY` and `GITHUB_WEBHOOK_SECRET` in Cloudflare, wire the migration runner to process queued `migration_pr` jobs, then run one sandbox end-to-end PR.

## [DECISION-7] Discord support server (optional)
- **Status:** RESOLVED — default applied
- **Decision:** SKIP for week 1
- **Substitute:** GitHub Discussions is the support surface; the LLM-on-rails bot answers via Discussions comments (Workers AI free tier)
- **Reconsider:** after first $1K revenue clears

## [DECISION-8] Sole-prop / LLC for AWS Marketplace
- **Status:** RESOLVED — default applied (deferred)
- **Decision:** SKIP until first $1K revenue clears
- **AWS Marketplace listing:** files staged in `marketplace/aws/` (TBD); listing submission gated on entity formation funded from revenue (~$0–$50 in most US states)

## [DECISION-9] Email-from address
- **Status:** RESOLVED — default applied
- **Decision:** `Rupture <noreply@ntoledo319.github.io>` (Resend handles SPF/DKIM)
- **Custom domain:** deferred per DECISION-2

## [DECISION-10] Refund window
- **Status:** RESOLVED — default applied
- **Decision:** 7 days from PR open (or PR close, whichever first)
- **Behavior:** `apps/worker/src/github.ts` watches `check_run.completed`; if `conclusion=failure` and the buyer hasn't applied an `override-refund` label within 7 days, Stripe refund auto-fires
- **Override:** operator can set `REFUND_WINDOW_DAYS` env var to 14 or 30 if a customer requests

---

## Launch Mode

Rupture is no longer in dry-launch for Audit PDF or Migration Pack checkout. GitHub Pages, production Worker health, CI, benchmark, signed `v1.0.0` release artifacts, and VS Code Marketplace publishing are green.

Remaining launch gates are limited to the GitHub Action Marketplace listing propagation/publication, the real Migration Pack sandbox PR test, and distribution. The sandbox PR is blocked by missing GitHub App private key/webhook secret plus the external migration runner wiring. Show HN should wait for the Tuesday/Wednesday launch window; from Saturday May 2, 2026, the next suitable windows are Tuesday May 5, 2026 or Wednesday May 6, 2026.
