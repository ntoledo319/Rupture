# Rupture — Autonomous Agent Runbook

> This document is the single source of truth for an AI agent to take the Rupture project from its current state (3 MIT CLIs, no commerce, no distribution, no recurring revenue) to a fully self-serving, $0-seed, autonomous business with a $25K/7-day target and ongoing MRR. The agent reads this end-to-end, executes top-to-bottom, and surfaces only the explicit `[DECISION]` blocks below to the operator.

---

## 0. Operating rules — non-negotiable, applied to every step

1. **$0 seed money.** No paid SaaS, no paid hosting, no paid auditors, no paid contractors, no paid ads, no paid domain (until first revenue clears). Free tiers and OSS only. Every cent spent must come from revenue that has *already* landed.
2. **Fully autonomous.** Every SKU terminates in a webhook, not a human. Every support touch is a bot or a doc. Every trust signal is code or telemetry, not a testimonial. If a step needs a human, it does not exist.
3. **Legal + ToS-compliant on every platform touched.** GitHub, Stripe, AWS, Cloudflare, npm, PyPI, VS Code Marketplace, Google Search, Discord — we follow each platform's ToS, anti-spam, anti-abuse, trademark, and content rules to the letter. Anything borderline (mass cold outreach, scraping behind auth, unsolicited PRs to repos that didn't opt in, trademark misuse, deceptive pricing) is cut.

If any task in this runbook violates any of these rules, the agent stops and surfaces the conflict to the operator. The agent never silently bends a rule.

---

## 1. Mission summary

**Current state:** Three working MIT-licensed CLIs (`lambda-lifeline`, `al2023-gate`, `python-pivot`) with 116 passing tests. A landing page on a third-party host. A README with a $499/$999/$2,499 ladder that violates the autonomy rule (offers human support).

**Target state:** A fully autonomous, $0-seed system that:
- Sells four self-serve SKUs (CLI free, Audit PDF $299–$599, Migration Pack $1,499, Org License $14,999/yr) plus a Drift Watch subscription ($19/mo).
- Fulfills every order via webhooks within 5 minutes, no human in the loop.
- Distributes via a GitHub Action, VS Code extension, pre-commit hook, programmatic SEO pages, opt-in GitHub App, and an ICS deprecation calendar feed.
- Maintains itself: nightly benchmark, weekly mutation tests, auto-DLQ for failures, hard-capped free-tier resource use.
- Operates exclusively on free tiers (Cloudflare Workers, Pages, R2, Queues, Workers AI; GitHub Pages and Actions; PyPI; npm; VS Code Marketplace; Resend free tier; Sigstore).

**Revenue forecast (week 1):**
- Pessimistic: $1K–$4K
- Realistic: $9K–$22K
- Optimistic: $25K–$45K

Achieving $25K in week 1 requires the GitHub Action and VS Code extension to ship on schedule and a successful Show HN submission. The system survives indefinitely on free tiers regardless of week-1 outcome.

---

## 2. Operator decisions required (the only human-touch points)

The agent presents these as a single block at the start of execution. Defaults are listed; if the operator does not respond within 24 hours of the prompt, the agent proceeds with defaults and continues.

```
[DECISION-1] GitHub organization for hosting
  Default: ntoledo319 (existing personal account, repo already at github.com/ntoledo319/Rupture)
  Override only if: the operator wants to move to an org account.

[DECISION-2] Public-facing URL for launch
  Default: https://ntoledo319.github.io/Rupture (free, no domain purchase)
  Override only if: the operator buys a domain themselves and provides the name.

[DECISION-3] Stripe account
  Required: operator must create a free Stripe account (https://stripe.com/register) and provide a restricted API key (write: products, prices, payment_links, checkout, refunds; read: events).
  Blocking: this is the one credential the agent cannot self-issue. Until it lands, the agent runs the entire system in Stripe TEST MODE and proves the end-to-end flow with test cards. Switch to live mode is a single env-var flip the moment the key arrives.

[DECISION-4] Cloudflare account
  Required: operator creates a free Cloudflare account and a Workers API token with permissions for Workers, Pages, R2, KV, Queues, Workers AI. Free tier only.
  Blocking: deployment of the Worker stack. Until it lands, the agent develops locally with Wrangler dev and ships to a staging GitHub Pages mirror.

[DECISION-5] Resend (or alternative free email sender)
  Default: Resend free tier (3,000 emails/month, 100/day). Operator creates account, provides API key.
  Fallback if Resend unavailable: send via GitHub Actions + a Mailgun free tier (5,000 emails first 3 months) OR queue emails to be sent when SES is added later. Until any provider is configured, transactional emails are queued and the buyer sees a "delivery within 5 minutes — pending email provisioning" status.

[DECISION-6] GitHub App registration
  Required: operator clicks the install link the agent generates from the GitHub App manifest (https://docs.github.com/en/apps/sharing-github-apps/registering-a-github-app-from-a-manifest). One click; no further configuration.
  Blocking: the auto-PR bot (D4) and Migration Pack fulfillment.

[DECISION-7] Discord server (optional, deferrable)
  Default: skip in week 1; rely on GitHub Discussions for support. Spin up Discord only after first $1K of revenue.

[DECISION-8] Sole-prop/LLC formation for AWS Marketplace
  Default: defer until first $1K of revenue. Most US states allow $0–$50 sole-prop registration; pay from revenue.

[DECISION-9] Email-from address
  Default: noreply@<github-pages-url>. Resend handles SPF/DKIM via their domain if no custom domain owned.

[DECISION-10] Refund window
  Default: 7 days from PR merge (or PR close, whichever first). Refund auto-fires if the PR's CI failed without override.
  Override: operator can extend to 14 or 30 days.
```

Until DECISION-3, DECISION-4, and DECISION-6 are answered, the agent runs in **dry-launch mode**: code ships, fixtures pass, the landing page is live with "preorder" buttons that capture email but don't charge. The moment those credentials land, dry-launch flips to live with one CI run.

---

## 3. Target repository layout

The agent restructures the repo to this shape. Existing content is preserved; new content is added.

```
Rupture/
├── README.md                    # rewritten per §5.A
├── LICENSE                      # MIT (existing)
├── SECURITY.md                  # bug-bounty + safe harbor language
├── CODE_OF_CONDUCT.md           # contributor norms
├── CONTRIBUTING.md              # rule-pack contribution flow
├── RULES.md                     # public sources for every rule shipped
├── BENCHMARK.md                 # nightly fleet results, auto-updated
├── updateplan.md                # this file
├── docs/                        # GitHub Pages root (existing, expanded)
│   ├── index.html               # rewritten per §5.A
│   ├── audit/                   # /audit upload + checkout
│   ├── pack/                    # /pack GitHub App install + checkout
│   ├── license/                 # /license enterprise checkout
│   ├── partners/                # /partners white-label signup
│   ├── status/                  # /status synthetic-check dashboard
│   ├── blog/                    # /blog auto-content loop output
│   ├── vs/                      # /vs/<competitor> programmatic pages
│   ├── migrate/                 # /migrate/<deprecation> SEO pages
│   ├── deprecations.ics         # public ICS calendar feed
│   ├── style.css
│   └── widget.js                # embeddable widget (D6)
├── kits/
│   ├── lambda-lifeline/         # existing, unchanged behaviour, hardened per §5.C
│   ├── al2023-gate/             # existing, unchanged behaviour, hardened per §5.C
│   └── python-pivot/            # existing, unchanged behaviour, hardened per §5.C
├── apps/
│   ├── web/                     # static site generator -> docs/
│   │   ├── build.py             # renders templates with rule-pack data
│   │   └── templates/
│   ├── worker/                  # Cloudflare Worker (TypeScript)
│   │   ├── src/
│   │   │   ├── index.ts         # router
│   │   │   ├── stripe.ts        # checkout + webhook + refunds
│   │   │   ├── github.ts        # GitHub App webhook handler
│   │   │   ├── upload.ts        # presigned R2 URL issuer
│   │   │   ├── license.ts       # /verify endpoint
│   │   │   ├── status.ts        # /status.json
│   │   │   ├── support.ts       # Workers AI rails bot
│   │   │   ├── partners.ts      # white-label endpoint
│   │   │   ├── ratelimit.ts     # token bucket
│   │   │   ├── caps.ts          # daily cost caps
│   │   │   └── idempotency.ts   # webhook replay protection
│   │   ├── wrangler.toml
│   │   └── test/
│   ├── runner/                  # containerized job (Python)
│   │   ├── Dockerfile
│   │   ├── main.py              # dispatches by SKU
│   │   ├── audit_pdf.py         # WeasyPrint renderer
│   │   ├── migration_pr.py      # opens PR via GitHub App
│   │   └── test/
│   ├── github-app/
│   │   ├── manifest.json        # GitHub App manifest (operator clicks to register)
│   │   ├── permissions.md       # minimum scopes only
│   │   └── README.md            # install instructions for buyers
│   ├── github-action/           # /rupture/check@v1 (D1)
│   │   ├── action.yml
│   │   ├── entrypoint.sh
│   │   └── README.md
│   ├── vscode-extension/        # (D2)
│   │   ├── package.json
│   │   ├── src/extension.ts
│   │   └── README.md
│   └── pre-commit/              # (D3)
│       └── hooks.yaml
├── rules/                       # rule packs (the moat — §5.B)
│   ├── public/                  # MIT, served on 7-day delay to free CLI
│   │   ├── lambda-nodejs.yml
│   │   ├── amazon-linux.yml
│   │   ├── lambda-python.yml
│   │   └── deprecations.yml     # source of truth for /deprecations.ics
│   └── private/                 # Org License only; never committed publicly
│       └── .gitkeep             # files ship via signed feed, not git
├── feed/                        # signed rule-pack publishing
│   ├── publish.py               # signs + uploads to feed.<domain>
│   └── verify.py                # CLI uses this to verify signatures
├── corpus/                      # public-repo PR data (B3); no private code
│   ├── catalog.md               # auto-generated catalog page
│   └── data/                    # JSON, anonymised/aggregated only
├── legal/
│   ├── terms.md                 # ToS from open template
│   ├── privacy.md               # Privacy Policy from Mozilla template
│   ├── dpa.md                   # DPA from gdpr.eu template
│   └── render.py                # renders to PDF via WeasyPrint
├── launch/
│   ├── show-hn-draft.md         # rewritten per §5.D
│   ├── blog-post.md             # rewritten — case-study style, no claimed history
│   └── hn-comments.md           # CUT (violates autonomy)
├── ledger/
│   ├── mission_ledger.md        # internal-only, not linked from public pages
│   └── FINAL_STATE.md           # internal-only
└── .github/
    ├── workflows/
    │   ├── test.yml             # runs pytest + npm test on every push
    │   ├── determinism.yml      # §5.C1
    │   ├── property.yml         # §5.C2
    │   ├── mutation.yml         # §5.C3 weekly
    │   ├── release.yml          # reproducible binary + SBOM + Sigstore
    │   ├── benchmark.yml        # nightly public-fleet run -> BENCHMARK.md
    │   ├── seo-pages.yml        # nightly -> docs/migrate, docs/vs
    │   ├── ics.yml              # nightly -> docs/deprecations.ics
    │   ├── blog-loop.yml        # weekly -> docs/blog/
    │   ├── deploy-worker.yml    # on push to main
    │   ├── deploy-pages.yml     # on push to main
    │   └── status-synth.yml     # every 5 min synthetic check
    └── dependabot.yml
```

---

## 4. Day-by-day execution plan

Each day below is a sequence of tasks. Each task has: **Goal**, **Inputs**, **Steps**, **Acceptance** (the test that must pass before moving on), and **On-failure** (what the agent does if acceptance fails).

The agent commits per task with a conventional-commit message, runs CI, and only proceeds when CI green. If CI red, the agent fixes and re-commits — never `--no-verify`, never amends pushed commits.

### Day 0 — Foundation, copy strip, free-tier scaffolding

**Task 0.1 — Strip human-implying language from README.md and docs/index.html.**
- Inputs: existing `README.md`, `docs/index.html`.
- Steps: remove the lines listed in §5.A "Hard removals." Replace pricing table per §5.A "New SKU table." Move all references off `sites.super.myninja.ai` to `https://ntoledo319.github.io/Rupture`.
- Acceptance: `grep -E "(1:1|priority Slack|live pairing|live migration|email support|🔥|Mission Complete|FINAL STATE|sites\.super\.myninja\.ai|operators who lived through)" README.md docs/index.html` returns nothing.
- On-failure: continue stripping until clean.

**Task 0.2 — Create `legal/` from open templates.**
- Inputs: Mozilla privacy template (https://www.mozilla.org/en-US/privacy/), Plain English Foundation ToS template, GDPR.eu DPA template.
- Steps: Download (via `curl`), edit names/dates/contact endpoint (use the GitHub Discussions URL as contact), commit. Render to PDF with WeasyPrint in a CI step.
- Acceptance: `legal/terms.pdf`, `legal/privacy.pdf`, `legal/dpa.pdf` exist and are reproducible (CI gate).
- On-failure: fall back to plain-Markdown linked from the landing page if WeasyPrint fails; defer PDF rendering to Day 2.

**Task 0.3 — Initialize `apps/web/build.py` static site generator.**
- Goal: single command `python apps/web/build.py` produces `docs/` from templates and rule-pack data.
- Steps: write `build.py` using `jinja2` only (stdlib + 1 dep). Templates render the new pricing table from `pricing.yml`. Build runs in CI, output committed to `docs/`.
- Acceptance: `python apps/web/build.py && git diff docs/` shows expected output; `make check` (or `pytest apps/web/test`) passes.

**Task 0.4 — Define SKUs in `pricing.yml`.**
- Steps: write `pricing.yml` with all five SKUs (CLI, Audit, Migration Pack, Org License, Drift Watch). Include surge-pricing tiers as a function of `days_until_deadline`. The Worker reads the same file at runtime.
- Schema:
  ```yaml
  skus:
    audit:
      stripe_product: prod_audit_pdf
      tiers:
        - max_days: 7
          price_usd: 599
        - max_days: 30
          price_usd: 399
        - max_days: 9999
          price_usd: 299
    migration_pack:
      stripe_product: prod_migration_pack
      price_usd: 1499
    org_license:
      stripe_product: prod_org_license
      price_usd: 14999
      interval: year
    drift_watch:
      stripe_product: prod_drift_watch
      price_usd: 19
      interval: month
  ```

**Task 0.5 — Surface the operator-decision block.**
- Steps: print the §2 decision block to the agent's standard output and block on those that block work. Continue with defaults for non-blocking decisions after a 24h timeout.
- Acceptance: a file `OPERATOR_DECISIONS.md` is written summarising the operator's responses (or defaults applied), committed to the repo.

**End-of-Day-0 state:** repo restructured per §3 skeleton, copy clean, legal docs in place, pricing config defined, decision block raised.

---

### Day 1 — Worker stack, Stripe wiring (test mode), free-tier guardrails

**Task 1.1 — Stand up `apps/worker/` Cloudflare Worker in TypeScript.**
- Inputs: DECISION-4 (Cloudflare token). If absent, develop locally with `wrangler dev` and skip deploy.
- Steps:
  - `cd apps/worker && npm init -y && npm i -D wrangler typescript @cloudflare/workers-types`
  - Write `src/index.ts` with the router and the endpoints listed in §3. Each endpoint is a thin file under `src/`.
  - Configure `wrangler.toml` with KV namespace `IDEMPOTENCY`, R2 bucket `RUPTURE_UPLOADS`, Queues binding `JOBS`, all on free tier.
- Acceptance: `wrangler dev` serves locally; `curl localhost:8787/health` returns `{ok:true}`. CI lints with `tsc --noEmit`.

**Task 1.2 — Stripe products + Payment Links via API (test mode first).**
- Inputs: DECISION-3 (Stripe key, may be test-mode only at this point).
- Steps:
  - Write `apps/worker/scripts/setup_stripe.ts` that uses the Stripe SDK to: create products, create prices for each SKU and tier, create Payment Links, write the resulting IDs to `pricing.yml`. Idempotent — re-runs do not duplicate.
  - Run with `STRIPE_KEY=sk_test_… node scripts/setup_stripe.ts`.
- Acceptance: Stripe dashboard (test mode) shows 5 products with the right prices; `pricing.yml` is updated; the Worker can checkout-redirect to a test Payment Link end-to-end with a `4242` test card.
- On-failure: if Stripe key missing, mark this task `pending` and continue Day 2; the landing page captures email instead of charging until live mode.

**Task 1.3 — Webhook handler with idempotency, DLQ, caps, rate-limits.**
- Steps: implement `src/stripe.ts` with:
  - HMAC signature verification using Stripe's library.
  - Idempotency: dedupe on `event.id` via Workers KV, 30-day TTL.
  - DLQ: any handler exception → push to a `JOBS-DLQ` queue → GitHub issue auto-opened by a separate worker that reads the DLQ.
  - Caps: every external call (Resend, R2 write, runner job) increments a daily counter in KV; if cap exceeded, queue with `delay_until=tomorrow_00:00_UTC` and email the buyer "your order is queued behind capacity, will process within 24h."
  - Rate-limit: token bucket per source IP and per buyer email.
- Acceptance: unit tests cover replay, exception → DLQ, cap exceeded → queue, rate-limit. `pytest apps/worker/test` green.

**Task 1.4 — Hash-anchored Audit PDF rendering.**
- Steps: in `apps/runner/audit_pdf.py`, render the buyer's audit using WeasyPrint. Embed in PDF metadata: `SHA-256(input)`, `rule_pack_version`, and a `verify_url` of the form `https://<host>/verify/<sha>`. The Worker `/verify/<sha>` endpoint returns `{valid: true, generated_at, rule_pack_version}` if it matches a known job.
- Acceptance: a test buyer journey produces a PDF whose embedded hash matches `sha256sum` of the input file.

**Task 1.5 — Resend integration with fallback.**
- Steps: `src/email.ts` calls Resend API. On 4xx/5xx, queue to `JOBS-EMAIL` for retry with exponential backoff (3 attempts, then DLQ).
- Acceptance: integration test against Resend test key; mock-mode produces a renderable email.

**End-of-Day-1 state:** Worker deployed (or dev-only if Cloudflare token absent), Stripe wired in test mode, every webhook is idempotent, capped, rate-limited, and DLQ'd. Audit PDFs are hash-anchored.

---

### Day 2 — Runner container, deterministic builds, severity scoring, upsell

**Task 2.1 — Containerize `apps/runner/`.**
- Steps: Multi-stage `Dockerfile` (slim Python base, install all 3 kits + WeasyPrint). `main.py` reads a job descriptor from stdin (`{sku, buyer_id, input_url, output_target}`), executes, exits 0 on success, non-zero with a structured error on failure. Image published to `ghcr.io/ntoledo319/rupture-runner:<sha>` from CI.
- Acceptance: `docker run -i ghcr.io/.../rupture-runner < test/fixtures/audit-job.json` produces the expected PDF.

**Task 2.2 — Determinism CI gate (C1).**
- Steps: a CI job runs each kit twice on the same fixture and `diff`s the output. Fails the build on byte-difference. Strip non-deterministic PDF metadata (timestamp, generator string) before comparing.
- Acceptance: `.github/workflows/determinism.yml` passes; PDFs print "Deterministic ✅" in the cover.

**Task 2.3 — Severity × blast-radius scoring (G1).**
- Steps: extend each rule's YAML with `severity: 1-10` and `blast_radius_factor: 0.1-1.0`. Findings sort by `severity * blast_radius_factor`. PDF includes a triaged top-10 list on page 1.
- Acceptance: snapshot test on a known fixture produces an expected ordering.

**Task 2.4 — Cost-of-not-fixing estimator (G2).**
- Steps: upload form has a one-line input "downtime cost in $/hour (optional, default $5,000)." PDF cover sheet computes `expected_loss = downtime_cost_per_hour * historical_outage_hours_for_this_deprecation`. The historical figure comes from a curated table in `rules/public/incidents.yml` with cited sources.
- Acceptance: cover sheet renders with an estimate; sources cited in an appendix.

**Task 2.5 — Roll-forward roadmap (G3).**
- Steps: PDF appendix lists the next 4 deprecations affecting the buyer's stack (computed from rule-pack `deprecations.yml`) with dates, plus an in-PDF link to `/drift-watch?prefill=<token>` that pre-fills the buyer's data into the Drift Watch checkout.
- Acceptance: appendix renders; the prefill link round-trips to checkout with the right plan.

**Task 2.6 — Property-based tests on codemods (C2).**
- Steps: install `hypothesis` (Python kits) and `fast-check` (lambda-lifeline). Generate random valid JS/Python AST inputs, assert codemod output is still valid AST and roundtrips through parse/print.
- Acceptance: `pytest -k property` passes; coverage of codemod branches ≥ 90%.

**End-of-Day-2 state:** runner is deterministic, hash-anchored, triage-aware, cost-aware, upsell-aware, and property-tested.

---

### Day 3 — GitHub App, Migration Pack, refund guarantee, deprecations.ics

**Task 3.1 — GitHub App manifest.**
- Steps: write `apps/github-app/manifest.json` with:
  - Permissions (minimum): `contents:write`, `pull_requests:write`, `metadata:read`, `checks:read`.
  - Events: `push`, `pull_request`, `check_run`, `installation`.
  - Webhook URL: `https://<worker-host>/github/webhook`.
  - User-facing name: "Rupture Migration Bot."
  - Public install page: `https://<host>/pack/install`.
- Operator action (DECISION-6): click `https://github.com/settings/apps/new?manifest=<base64-of-manifest>` to register. The agent generates this URL and surfaces it.
- Acceptance: `/pack/install` redirects to the GitHub App install page; on install, our webhook receives `installation: created` and stores the install ID in KV.

**Task 3.2 — Migration Pack PR opener (`apps/runner/migration_pr.py`).**
- Steps: on Stripe checkout success, the Worker enqueues a job. The runner: clones the buyer's repo via the GitHub App token, runs the kit, creates a branch `rupture/migrate-<sku>-<sha>`, opens a PR with body containing a structured summary, the rule-pack version hash, and a "Refund auto-fires if CI fails after 7 days" footer.
- Acceptance: end-to-end test against a sandbox repo `ntoledo319/rupture-sandbox` produces a PR.

**Task 3.3 — Refund auto-fire (A5).**
- Steps: on `check_run.completed` for the migration PR, if `conclusion=failure` and 7 days elapsed without an `override:` label from the buyer, fire `stripe.refunds.create(charge_id)`.
- Acceptance: simulated failure → refund issued in Stripe test mode.

**Task 3.4 — `/abuse` endpoint and `.no-rupture` opt-out (F3).**
- Steps: `POST /abuse` with `{repo}` pauses the bot for that repo within 60s by writing to KV. The auto-PR bot checks the `.no-rupture` file at the repo root before any action; presence = skip.
- Acceptance: posting to `/abuse` for a test repo prevents subsequent PRs to that repo.

**Task 3.5 — Public deprecation calendar (D7).**
- Steps: `.github/workflows/ics.yml` runs nightly, reads `rules/public/deprecations.yml`, emits a valid RFC-5545 `.ics` to `docs/deprecations.ics`.
- Acceptance: subscribing to the URL in Google Calendar / Apple Calendar populates events with correct dates and descriptions.

**End-of-Day-3 state:** Migration Pack flow is end-to-end on a sandbox repo, refund guarantee is enforced by code, abuse-handling is live, public ICS feed is published.

---

### Day 4 — Auto-PR bot (opt-in only), GitHub Action, pre-commit hook, public benchmark

**Task 4.1 — Auto-PR bot, opt-in only.**
- Critical constraint: **only operates on repos that have explicitly installed the GitHub App.** No cold mass-PRs to public repos that did not opt in. This is the difference between Renovate (legitimate) and a banned spam bot.
- Steps:
  - On `installation: created`, scan the installed repos for affected runtimes (read-only, via the granted scope).
  - For each affected repo, schedule one PR with a 60-second jitter to avoid thundering-herd.
  - Throttle: max 5 PRs per installation per day, max 1 PR per repo per week.
  - Each PR body links to `/abuse` and to the `.no-rupture` opt-out doc.
- Acceptance: install on the sandbox, see one PR; install on a second repo with `.no-rupture` present, see no PR; abuse-report → no further PRs.

**Task 4.2 — `rupture/check@v1` GitHub Action (D1).**
- Steps: write `apps/github-action/action.yml` and `entrypoint.sh`. Action: runs the kit on the workspace, comments findings on the PR with a link to `/audit?prefill=<token>` for the full report.
- Steps to publish: tag `v1.0.0`, write `apps/github-action/README.md`, list on GitHub Marketplace (free).
- Acceptance: a test workflow in `rupture-sandbox` runs the Action and produces a PR comment.

**Task 4.3 — Pre-commit hook (D3).**
- Steps: write `apps/pre-commit/hooks.yaml` declaring three pre-commit hooks (one per kit). Publishable to the pre-commit ecosystem with a `git tag` — no central registration.
- Acceptance: `pre-commit try-repo .` against a fixture catches the expected violations.

**Task 4.4 — Nightly public benchmark (`.github/workflows/benchmark.yml`).**
- Steps: maintain a curated list of 50 public repos with affected runtimes (in `corpus/public-repos.txt`). Nightly job: clone (read-only), run each kit, record `pass/fail/warn`, publish to `BENCHMARK.md` and `docs/status/benchmark.json`.
- ToS note: every action is read-only, complies with each repo's LICENSE for static analysis, and emits no PRs (PRs only happen on opt-in installs per 4.1).
- Acceptance: `BENCHMARK.md` updates nightly with a stable schema.

**End-of-Day-4 state:** auto-PR bot is opt-in and throttled; the GitHub Action is on the Marketplace; the public benchmark runs nightly.

---

### Day 5 — Programmatic SEO, white-label, embeddable widget

**Task 5.1 — `/migrate/<deprecation>` pages (D5 first half).**
- Steps: for each deprecation entry in `rules/public/deprecations.yml`, render a page at `docs/migrate/<slug>/index.html`. Page contains: deadline, breaking changes, code examples (from the kit's test fixtures), "Run the audit" CTA.
- Acceptance: `find docs/migrate -name index.html | wc -l` ≥ 30; sitemap includes them; pages validate against schema.org `TechArticle`.

**Task 5.2 — `/vs/<competitor>` pages (D5 second half).**
- Constraint: factual only. No logos. Plain-text product names under nominative fair use. Each fact has an "as of YYYY-MM-DD" timestamp and links to the competitor's official source.
- Steps: write a generator that pulls factual data (license, last-commit date, GitHub stars, npm/PyPI publish date) via public APIs respecting their rate limits. Render the page as a feature comparison table.
- Acceptance: no trademark misuse audit (`grep -i logo docs/vs/` empty); each factual claim cites a URL.

**Task 5.3 — Sitemap + Search Console submission.**
- Steps: generate `docs/sitemap.xml`. Submit via Google Search Console Submission API (free, requires no payment, just DECISION-1's GitHub-pages domain to be verified — verification is a one-time DNS-or-HTML token; HTML-token is free and instant on GitHub Pages).
- Acceptance: Search Console shows the sitemap as accepted.

**Task 5.4 — White-label `/partners/*` endpoint (A4).**
- Steps:
  - `POST /partners/signup` creates a Stripe Connect Express account for the partner.
  - `POST /partners/<slug>/audit` accepts a buyer file + Stripe Checkout Session ID, runs the audit branded with the partner's logo (uploaded at signup, validated against partner's domain via DNS TXT record to prevent impersonation).
  - Stripe Connect splits revenue 70/30 automatically.
- Acceptance: end-to-end test: sandbox partner → branded PDF → Stripe Connect transfer.

**Task 5.5 — Embeddable widget (D6).**
- Steps: `docs/widget.js` renders a "Check your AWS deprecation exposure" button that POSTs an anonymous fingerprint and redirects to `/audit?ref=<embedder-id>` with a Stripe Connect attribution. Self-disclosing — the widget includes an info icon explaining what data is collected (just the fingerprint and the host page URL, no third-party cookies).
- Acceptance: integration test: include `widget.js` on a static page, click → land on `/audit` with `ref` param preserved.

**End-of-Day-5 state:** SEO surface is live (~150 pages); white-label channel is operational; embeddable widget is shippable.

---

### Day 6 — Quality gates, reproducible release, support bot, status page

**Task 6.1 — Mutation testing (C3).**
- Steps: `mutmut` for Python kits, `stryker` for lambda-lifeline. `.github/workflows/mutation.yml` runs weekly. If score drops below 80%, auto-open a `quality-debt.md` issue.
- Acceptance: first run produces a baseline score; the issue-opener works on a deliberately-broken commit.

**Task 6.2 — Reproducible single-binary release (C4).**
- Steps: `shiv` for the Python kits, `ncc` + `pkg` for lambda-lifeline. CI builds twice in parallel containers; a third job `diff`s the SHAs.
- Acceptance: `release.yml` produces a single binary per kit per platform; SHAs match across two builders.

**Task 6.3 — SBOM + Sigstore signing (C5).**
- Steps: `cyclonedx-py` + `cyclonedx-bom` (npm) generate SBOMs; `cosign sign-blob --keyless` signs each binary using Sigstore's free OIDC-anchored flow.
- Acceptance: `cosign verify-blob` round-trips on the published binary.

**Task 6.4 — `/status` synthetic-check dashboard (E4).**
- Steps: `.github/workflows/status-synth.yml` runs every 5 minutes, exercises the full Stripe-test → Worker → runner → email loop. Pushes results to `docs/status/data.json`. Dashboard renders from that.
- Acceptance: a deliberate Worker outage flips the dashboard to red within one cycle.

**Task 6.5 — LLM-on-rails support bot (E6).**
- Steps:
  - `apps/worker/src/support.ts` exposes `POST /support/ask`. Body: `{question}`. The handler concatenates a system prompt + the kit READMEs + BENCHMARK.md + a curated FAQ, sends to Cloudflare Workers AI free-tier model (`@cf/meta/llama-3.1-8b-instruct`), and returns the answer **only** if the model output cites a known doc URL pattern (regex check) and the question is in-scope (classifier with rules first, model second).
  - Daily-cap check: if Workers AI free-tier exhausted, fall back to a canned `"See docs at https://..."` reply.
  - GitHub Discussions integration: a poller reads new questions and posts the bot reply as a comment with `[bot]` prefix and a "this is an automated response" disclaimer.
- ToS: Discord ToS and GitHub Discussions ToS both permit bots with disclosure.
- Acceptance: ask three known-FAQ questions, get correct answers with valid doc citations; ask an out-of-scope question, get a polite refusal with a docs link.

**End-of-Day-6 state:** quality gates green; releases reproducible and signed; status page live; support is autonomous.

---

### Day 7 — Launch

**Task 7.1 — Final dry-run of the entire purchase flow.**
- Steps: from a clean browser session, walk through Audit, Migration Pack, Org License, Drift Watch using Stripe test cards. Verify: PDF arrives in <5 min, PR opens within 5 min, license key issued, subscription appears in Stripe.
- Acceptance: all four paths complete; metrics increment on `/status`.

**Task 7.2 — Flip Stripe to live mode.**
- Pre-condition: DECISION-3 fully resolved with a live key.
- Steps: rotate the env var via `wrangler secret put STRIPE_KEY`. Re-run `setup_stripe.ts` in live mode to create live products.
- Acceptance: a real $1 charge on a real card succeeds end-to-end (then refunded automatically by a `cleanup_test.ts` script).

**Task 7.3 — Submit Show HN.**
- Steps:
  - Generate the post body from the rewritten `launch/show-hn-draft.md` (per §5.D).
  - Submit URL: `https://github.com/ntoledo319/Rupture`.
  - Body lead: "I built three CLIs that migrate AWS off deprecated runtimes. Audit PDFs and PR-bot tiers are paid; CLIs are MIT. Public benchmark, hash-anchored reports, deterministic builds." No claimed operator history.
  - Day/time: the operator clicks Submit during a Tuesday or Wednesday 8:00–10:00 PT window. Agent surfaces this as `[DECISION-7-launch-window]` if the operator wants to pre-schedule.
- Post-submit: agent does NOT pre-stake comments. If comments arrive, the autonomous support bot may answer in-scope questions; out-of-scope replies stay silent.

**Task 7.4 — Crowdsourced rule bounty live (B2).**
- Steps: `/contribute` accepts rule PRs. CLA-bot enforces contributor agreement. CI runs the rule against the test fleet. On merge, a Stripe Promotion Code is generated and emailed to the contributor (Audit credit, not cash).
- Acceptance: a sandbox PR earns a real promotion code redeemable on `/audit`.

**Task 7.5 — Migration corpus catalog (B3).**
- Steps: nightly job aggregates anonymised stats from opted-in installations only (no private code, no per-buyer attribution). `corpus/catalog.md` renders the public summary.
- Acceptance: catalog page exists with at least the seed-fleet data; private data audit (`grep -r '/private/' corpus/data/`) returns empty.

**Task 7.6 — VS Code extension published (D2).**
- Steps: `vsce publish` to the Marketplace under the operator's free Microsoft publisher account (DECISION operator must create publisher; it's free).
- Acceptance: the extension page goes live on Marketplace and a clean install on a fresh VS Code instance lights up squigglies on a fixture file.

**End-of-Day-7 state:** Launched. Stripe live. Show HN posted. Bounty live. Catalog live. Extension published.

---

## 5. Implementation reference (the things the agent looks up while executing days 0–7)

### 5.A. Public-facing copy — what changes in README.md and docs/index.html

**Hard removals (must not appear anywhere customer-facing):**
- "Email support for 90 days / 1 year / forever"
- "Live migration pairing"
- "Priority Slack"
- "1:1 support"
- "🔥 Ship-ready"
- "Mission Complete"
- "FINAL STATE"
- "operators who lived through these migrations"
- "we built this the third time we had to migrate a fleet by hand"
- Any URL containing `sites.super.myninja.ai`

**New SKU table** (replaces the existing $499/$999/$2,499 table):

| SKU | Price | What you get | Delivery |
|---|---|---|---|
| **CLI (free)** | $0 | All three kits, MIT, no limits | `git clone` |
| **Audit PDF** | $299 (surge to $399 inside 30 days, $599 inside 7 days) | A hash-anchored, deterministic report scoring every finding by severity × blast-radius, with a roll-forward roadmap and cost-of-not-fixing estimate | Email within 5 minutes |
| **Migration Pack** | $1,499 | A real PR opened on your repo with codemods + IaC patches + canary plan + rollback. Refund auto-fires if CI fails | GitHub App opens PR within 5 minutes |
| **Org License** | $14,999 / yr | Live rule-pack feed, private rule extensions, unlimited runs, one-year validity | License key emailed |
| **Drift Watch** | $19 / mo | Weekly re-scan of a read-only IAM role; delta PDF on change; auto-PR on new deprecation | Cron-driven |

**New hero copy** (README and `index.html`):

> **Rupture migrates AWS workloads off deprecated runtimes — automatically, deterministically, and before the deadline.**
> The CLIs are MIT-licensed and open source. The paid tiers handle the parts that matter to a busy team: a hash-anchored audit report, a real PR opened on your repo, a license for your whole org, and a watch process that catches the next deprecation before it reaches you.
> Three kits today (Lambda Node 20, Amazon Linux 2, Lambda Python 3.9–3.11). New kits ship as new deadlines emerge.

### 5.B. Rule-pack signed feed

- File format: YAML, schema-versioned.
- Hosting: free GitHub Pages at `https://ntoledo319.github.io/Rupture/feed/`.
- Signing: Sigstore keyless. Every pack has a `.sig` and a `.bundle` published alongside.
- Free CLI: pulls `https://.../feed/public/<pack>.yml?delay=7d`. The 7-day delay is enforced by the build pipeline writing a `valid_after` timestamp into a parallel manifest the CLI checks.
- Org License: pulls from a separate signed feed with no delay.
- Verification: `feed/verify.py` is invoked by the kit on every run and refuses to run if the signature is invalid or expired.

### 5.C. Code-quality gates (the C-series tasks unified)

- **C1** — determinism (Day 2.2)
- **C2** — property tests (Day 2.6)
- **C3** — mutation tests (Day 6.1)
- **C4** — reproducible binaries (Day 6.2)
- **C5** — SBOM + Sigstore (Day 6.3)
- **C6** — schema validation (folded into all `apps/*` code; Pydantic v2 / Zod everywhere)

The release process (`.github/workflows/release.yml`) gates on: tests green AND determinism green AND property green AND mutation score ≥ 80% AND SBOM generated AND signature verifies. Any failure blocks the release.

### 5.D. Show HN draft (rewritten — to replace `launch/show-hn-draft.md`)

```
Title: Show HN: Rupture — three CLIs for AWS runtime deprecation deadlines (MIT)

Body:
I built three CLIs that automate AWS migrations off deprecated runtimes:

- lambda-lifeline   Node.js 16/18/20 → 22  (Apr 30, 2026)
- al2023-gate       Amazon Linux 2 → AL2023 (Jun 30, 2026)
- python-pivot      Lambda Python 3.9/3.10/3.11 → 3.12

Each kit does the same five things: scan the account, run mechanical
codemods (dry-run by default), patch IaC (SAM / CDK / Terraform / Serverless),
generate a staged canary deploy plan, and produce a tested rollback script.

What's interesting under the hood:

- Deterministic builds: same input → byte-identical output (CI-gated).
- Hash-anchored reports: every audit PDF embeds SHA-256 of inputs and the
  rule-pack version, with a public verification URL.
- Property-based and mutation-tested codemods.
- Sigstore-signed releases with CycloneDX SBOMs.
- Public nightly benchmark on 50 real public IaC files.

Free, MIT, on GitHub. Paid tiers (audit PDF, PR-bot, license, watch) all
self-serve via webhook — no humans in the loop.

Repo: https://github.com/ntoledo319/Rupture
Benchmark: https://ntoledo319.github.io/Rupture/status/benchmark.json
Sample audit PDF: https://ntoledo319.github.io/Rupture/audit/sample.pdf
```

The `launch/hn-comments.md` (pre-staked human replies) is **deleted** — that pattern violates the autonomy rule.

### 5.E. Free-tier infrastructure budget

| Service | Free tier | Used for | Cap-handling |
|---|---|---|---|
| Cloudflare Workers | 100K req/day | All webhooks, API endpoints | Token bucket + queue overflow |
| Cloudflare Pages | Unlimited static | Landing, status, blog, docs | n/a |
| Cloudflare R2 | 10 GB / 1M reads / 10M writes | PDF storage, upload staging | Auto-purge buyer files at 30 days |
| Cloudflare Queues | 1M ops/month | Job queue, DLQ | Backoff if approaching cap |
| Cloudflare Workers AI | 10K neurons/day | Support bot, contributor PR review | Fallback to canned response |
| Cloudflare KV | 100K reads/day, 1K writes/day | Idempotency, rate-limit, caps | Cache write-through, then short-circuit |
| GitHub Pages | Unlimited public | Rule-pack feed, status, blog, SEO | n/a |
| GitHub Actions | Unlimited public, 2K min/month private | All CI, nightly fleet, rule-pack publish | Keep all repos public |
| GitHub Apps | Free | Auto-PR bot (opt-in only) | n/a |
| GitHub Marketplace | Free | List the Action | n/a |
| Stripe | $0 setup, per-txn fee | Checkout, refunds, Connect | Fees come out of revenue, not seed |
| Resend | 3,000/month, 100/day | Transactional email | Queue overflow + buyer notification |
| PyPI / npm | Free | Package distribution | n/a |
| VS Code Marketplace | Free | Extension distribution | n/a |
| Sigstore | Free, keyless | Release signing | n/a |
| Domain | $0 if `*.github.io` | Customer-facing URL | Defer custom domain until first $50 of revenue |

### 5.F. Cut / deferred — what is explicitly NOT being built (so nothing is smuggled past the rules)

| Idea | Why cut/deferred |
|---|---|
| Cold email outreach | Requires paid sender reputation tooling, physical mailing address, manual list curation. Breaks autonomy and $0-seed. |
| Auto-PR bot opening cold PRs on un-installed public repos | Violates GitHub's anti-spam policy. **Replaced** with opt-in via GitHub App install. |
| iubenda / Termly auto-legal | Paid SaaS. Replaced with self-hosted from open templates. |
| SOC 2 Type 1 via Vanta/Drata | $8K/yr. Deferred until revenue funds it; controls implemented now. |
| AWS Marketplace SaaS listing (immediate) | Requires a registered business entity. Stubs prepared; submission deferred until sole-prop/LLC formed (~$0–$50 from revenue). |
| Custom `.com` domain | $10/yr is non-zero. Defer until first $50 of revenue clears; launch on `*.github.io`. |
| Paid LLM API for support bot | Replaced with Cloudflare Workers AI free tier + canned-fallback. |
| Logos on `/vs/*` comparison pages | Trademark risk. Replaced with plain-text product names under nominative fair use. |
| Cash bug-bounty payouts pre-revenue | No seed cash to pay. Bounty page lives, payouts triggered only after revenue clears. |
| Crowdsourced rules paid in cash | Replaced with Audit credits (in-system coupons), avoids securities/tax complexity. |
| Scraping behind authentication / using buyer creds without explicit role-based consent | Always cut. Buyer always provides a read-only IAM role they control. |
| Storing buyer code in the public migration corpus | Always cut. Corpus is public-repo data only; private code is firewalled in code. |
| Pre-staked Show HN comments by a human | Violates autonomy. Cut. The bot may answer in-scope questions only. |
| Telemetry / analytics on the CLI | The CLI is offline-first by design. No telemetry without explicit `--telemetry-on`. |

---

## 6. Ongoing autonomous loop (post-launch, indefinite)

The system maintains itself. The agent's run continues after Day 7 with the following recurring jobs, all driven by `.github/workflows/*` and Cloudflare Cron Triggers:

| Cadence | Job | Purpose |
|---|---|---|
| Every 5 minutes | Status synth | Detect outages, flip dashboard |
| Every 15 minutes | DLQ-drainer | Open GitHub issues for any stuck jobs |
| Hourly | Drift Watch worker | Re-scan accounts whose subscription cycle is due |
| Daily | SEO regen | Rebuild `/migrate/*` and `/vs/*` pages from latest rule data |
| Daily | ICS regen | Update `docs/deprecations.ics` |
| Daily | Cap reset | Reset daily counters at 00:00 UTC |
| Weekly | Mutation tests | Quality regression detection |
| Weekly | Blog auto-loop | One paragraph: "this week: N PRs opened, N merged, N rules added" |
| Nightly | Public benchmark | Update `BENCHMARK.md` |
| Nightly | Corpus aggregation | Update `corpus/catalog.md` from opt-in install data |
| Monthly | Rule-pack release | Sign and publish new public/private packs |
| Monthly | Free-tier audit | Verify usage stays under all caps; alert if any cap >80% utilised |
| Quarterly | New deprecation scan | Scrape AWS What's New (a public RSS feed) for new deprecation announcements; auto-open issues for candidate kits |

If at any point a job exceeds its free-tier budget for the day, it self-pauses and rolls forward.

---

## 7. Failure modes and self-recovery

The agent encodes recovery for each named failure:

| Failure | Recovery |
|---|---|
| Stripe webhook 5xx | Idempotency key + Cloudflare Queues retry, exponential backoff, DLQ → GitHub issue. |
| Resend rate limit | Email job re-queued with `delay=24h`. Buyer notified on `/status`. |
| Cloudflare Worker hits 100K/day | Queue overflow with 24h delay; static landing page still works. |
| GitHub App suspended | Migration Pack flow disabled with clear `/status` red. Audit and Drift Watch unaffected. Operator alerted via DLQ-issue. |
| Free-tier domain expires | n/a — `*.github.io` doesn't expire. |
| Stripe live key compromise | `wrangler secret put STRIPE_KEY` rotates instantly; refund any unauthorised charges via API. |
| Determinism CI fails | Block release; auto-bisect to identify the offending change; open issue with the diff. |
| Mutation score drops below 80% | Auto-issue opened; release still allowed once but flagged. Two consecutive drops blocks release. |
| Bot PR is rejected with hostile feedback | The bot does not respond. The maintainer-bot opens an internal issue tagged `tone-review` for human (operator) review. |
| Buyer disputes a charge | Stripe dispute auto-acknowledged with the hash-anchored PDF as evidence. |
| Workers AI free tier exhausted | Support bot falls back to canned "see docs" response. |
| Catastrophic auth abuse on `/upload` | Token-bucket clamps; CAPTCHA fallback served from the static page. |

Any failure not in this table escalates to an auto-opened GitHub issue with the redacted payload, tagged `agent-attention`. The operator is the audience for those issues; the agent does not page them otherwise.

---

## 8. Acceptance criteria for the entire run

The agent considers the mission complete when **all** of the following are true:

- [ ] `OPERATOR_DECISIONS.md` exists with all 10 decisions resolved (or defaults applied with operator-acknowledged 24h timeout).
- [ ] `README.md` and `docs/index.html` are scrubbed of every banned phrase in §5.A.
- [ ] All four checkout flows (Audit, Migration Pack, Org License, Drift Watch) succeed end-to-end against Stripe live mode within 5 minutes.
- [ ] `BENCHMARK.md` updated within the last 24 hours.
- [ ] `docs/deprecations.ics` valid RFC 5545.
- [ ] Determinism CI passing on `main`.
- [ ] Property tests passing.
- [ ] Mutation score ≥ 80%.
- [ ] Latest release has a CycloneDX SBOM and a verifiable Sigstore signature.
- [ ] GitHub App installed on at least one repo (the operator's `rupture-sandbox`); a real PR has been opened by the bot.
- [ ] `rupture/check@v1` listed on GitHub Marketplace.
- [ ] VS Code extension listed on the Marketplace.
- [ ] `/status` reports green on every component for at least 1 hour.
- [ ] No paid service active beyond Stripe (post-revenue) and possibly Resend free tier.
- [ ] Show HN post submitted (timestamp recorded in `launch/launched.txt`).

When all items check, the agent files a `MISSION_COMPLETE.md` in `ledger/` (internal, not customer-facing), then transitions to the §6 ongoing loop.

---

## 9. The principle, fully extended

> **Every SKU terminates in a webhook. Every failure terminates in a self-issued ticket. Every trust signal terminates in a verifiable hash. Every content artifact terminates in a CI job. Every support touch terminates in a doc URL. Every dollar spent comes from revenue, not seed. Every action taken on every platform respects that platform's ToS to the letter.**

The system observes itself, repairs itself, and expands its own surface area without intervention, without a budget, and without breaking a single rule of any platform it touches. That is the bar this runbook holds the agent to from the first commit to the indefinite ongoing loop.
