# Operator Decisions — Rupture Launch

> Source: `updateplan.md` §2. Each decision is either **RESOLVED** (operator answered or default applied after the 24h timeout) or **BLOCKING** (cannot proceed without operator input). Blocking items put the system in **dry-launch mode** (code ships, fixtures pass, landing live, no charges).

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
- **Status:** BLOCKING (live mode); RESOLVED for test mode
- **Test mode:** `STRIPE_KEY=sk_test_dummy_for_setup` placeholder; checkout flows render with test cards
- **Live mode prerequisite:** operator runs `stripe login` then sets `STRIPE_KEY` (standard live key `sk_live_...` or restricted key) via `wrangler secret put STRIPE_KEY`
- **Once live key lands:** the agent runs `apps/worker/scripts/setup_stripe.ts` to provision products, prices, payment links — idempotent

## [DECISION-4] Cloudflare account
- **Status:** BLOCKING for deployment; RESOLVED for development
- **Dev:** `wrangler dev` runs locally, integration tests pass
- **Deploy prerequisite:** operator creates a free Cloudflare account, sets `CF_API_TOKEN` as a GitHub Actions secret with permissions: Workers, Pages, R2, KV, Queues, Workers AI (free tier only)
- **Once token lands:** `.github/workflows/deploy-worker.yml` ships the Worker on every `main` push

## [DECISION-5] Resend (transactional email)
- **Status:** RESOLVED — default applied
- **Decision:** Resend free tier (3,000 emails/month, 100/day)
- **Operator action:** create free account; set `RESEND_API_KEY` as a Worker secret
- **Until secret lands:** emails are queued (`apps/worker/src/email.ts` returns `no_provider` and pushes to `JOBS-EMAIL`); buyers see "delivery within 5 minutes — pending email provisioning" on `/status`

## [DECISION-6] GitHub App registration
- **Status:** BLOCKING for Migration Pack and auto-PR bot; RESOLVED for everything else
- **Operator action:** click `https://github.com/settings/apps/new?manifest=<base64>` (URL emitted by `apps/github-app/manifest.json`); install on `ntoledo319/rupture-sandbox` for end-to-end test
- **Audit and Drift Watch:** unaffected by this decision and ship in dry-launch mode

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

## Dry-launch mode (active until DECISIONS-3, 4, 6 resolve)

While any of the three blocking decisions is still pending, the agent operates in **dry-launch**:
- Landing pages live; CTAs route to a "Pre-order — we'll email you when checkout opens" flow that captures `email + sku` to a queue
- All static pages, ICS feed, benchmark, and SEO surface still ship
- The `/status` page reflects which integrations are pending
- No real charges. No auto-PRs. No real emails (other than the pre-order capture).

The flip from dry-launch to live is a single CI run once each blocking secret lands.
