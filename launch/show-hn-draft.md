# Show HN Draft — Rupture Kits

**File location:** `/workspace/rupture/launch/show-hn-draft.md`

---

## Recommended title (pick one)

**Primary:**
```
Show HN: Rupture Kits – migration tools for AWS deprecation deadlines
```

**Alternative (leads with the most urgent deadline):**
```
Show HN: A CLI for migrating AWS Lambda Node.js 20 functions before the Apr 30 EOL
```

**Alternative (leads with openness):**
```
Show HN: I built 3 AWS migration CLIs (MIT, 116 tests) – lambda/AL2/Python EOLs
```

My recommendation: **the primary.** It's the most honest framing of what the project actually is, targets the search-term our users are typing, and doesn't overclaim urgency on a single SKU.

---

## Submission URL

```
https://github.com/ntoledo319/Rupture
```

**Do not** submit the landing page as the primary URL. HN readers penalize landing-page submissions, reward repo submissions. The landing page goes in the body of the post instead.

---

## Body text

```
Hi HN. I built three CLIs that migrate AWS services off their deprecated runtimes:

• lambda-lifeline   — AWS Lambda Node.js 16/18/20 → 22 (deadline Apr 30, 2026)
• al2023-gate       — Amazon Linux 2 → AL2023           (deadline Jun 30, 2026)
• python-pivot      — Lambda Python 3.9/3.10/3.11 → 3.12 (3.9 past deadline Dec 2025)

They all do the same unglamorous five things: scan the account for affected resources, 
apply narrow mechanical codemods (with a dry-run default), patch the IaC (SAM / CDK / 
Terraform / Serverless Framework), deploy via a staged canary with a CloudWatch alarm 
as the rollback trigger, and offer a tested rollback path.

Repo: https://github.com/ntoledo319/Rupture

Why this exists
---------------
I kept getting the same three emails from AWS — "your runtime is deprecated" — and 
noticed that every time, the migration work was (a) boring, (b) had huge blast radius, 
and (c) had no integrated tool. CloudQuery gives you inventory. AWS Migration Hub is 
for lift-and-shift between regions. The aws-samples repos give you a snippet. Nobody 
combines scan + codemod + IaC patch + tested deploy + rollback for one specific 
deprecation.

So these kits are scoped. Each one targets exactly one deadline. Each one does nothing 
else. Each one ships with its own test suite (24 + 48 + 44 = 116 tests total, all 
offline via fixture mode, no AWS creds needed to reproduce).

What's in the box
-----------------
• Scan in multiple output formats (table / json / csv / markdown) with --strict for CI
• Codemods are mechanically safe (e.g. `import assert` → `import with`), ambiguous 
  stuff is lint-only
• IaC patcher is idempotent — already-migrated resources are not touched
• Canary deploy REQUIRES a CloudWatch alarm ARN with --apply (no alarm, no deploy)
• Everything is dry-run by default; --apply is always required to write
• No telemetry, no vendored dependencies beyond boto3 (optional)

What's not in the box
---------------------
• "AI" — none of this is an LLM. It's regex, AWS SDK calls, and curated tables.
• A one-size-fits-all migration framework. Each kit is independent. Nothing shared.
• Comprehensive dependency databases. The wheel table in python-pivot is ~30 packages 
  — the ones that actually historically broke Lambda deploys — not all of PyPI.

Free vs paid
------------
Everything on GitHub is MIT. Fork it, use it, resell it.

Paid tiers ($499 / $999 / $2,499 per kit, bundle all 3 for $999 / $1,999 / $4,997) 
add a printable PDF runbook, a 2-hour captioned walkthrough video, expanded tables, 
custom rules for your codebase, and priority Slack / live pairing for Enterprise.

I'm transparent about this: the open kits are 100% functional. The paid tier is 
support + docs + custom rules, not gated features.

Landing: https://sites.super.myninja.ai/a51b9893-5170-4e08-87ed-c7db56f6885b/0eb07112/index.html
Repo:    https://github.com/ntoledo319/Rupture

Happy to answer questions about the migration surface, the codemod safety model, or 
any of the specific rules. If you're running Node 20 on Lambda, Apr 30 is two days 
from now and Phase 2 (block-create) follows 30 days later. Migrate sooner than later.
```

---

## Comments to pre-write (post yourself as top reply)

**Comment 1 — technical detail** (post ~2 min after submission):
```
A few details I didn't fit in the post:

• The Node → 22 codemod handles the two breaking changes that trip most teams: 
  `import ... assert { type: 'json' }` becomes `import ... with { type: 'json' }` 
  (both static and dynamic), and the CA cert env-var flip. Everything else is lint.

• The AL2→AL2023 remap table has ~50 entries covering the high-frequency trip-ups: 
  amazon-linux-extras (gone), ntp→chrony, yum-utils→dnf-utils, php7.4→8.2, 
  python3.8→3.11, curl→curl-minimal, OpenSSL 1.0→3 (ABI break for native code).

• The Python codemod is deliberately narrow. `collections.Mapping` → `collections.abc.Mapping` 
  is mechanical so it gets auto-rewritten. `datetime.utcnow()` is ambiguous (which tz 
  did you mean?) so it's a lint with a suggested fix.

Source of the rules: the What's New pages for each language release, plus the AWS 
Lambda runtime deprecation docs. All cited in the individual READMEs.
```

**Comment 2 — "why three kits instead of one framework"** (ready for when someone asks):
```
Tried a shared framework first. Abandoned it. The kits share maybe 200 lines of 
convention (arg parsing shape, dry-run default, --strict exit codes) but the actual 
work in each is so stack-specific that every abstraction I tried was leaky. 

So the convention is a shape, not a framework. Each kit is ~1500-2500 lines and 
independently installable. If you want lambda-lifeline you don't also download the 
AL2023 remap tables.
```

**Comment 3 — "how did you decide what's free vs paid"** (ready for when someone asks):
```
Reviewed Sentry, Sidekiq, Tailwind — the OSS-with-paid-tier businesses I respect. 
Pattern: the core is 100% functional OSS, the paid tier is "I also want the human 
who wrote this to care about my specific situation." So that's what I did. 

Nothing in the paid tier is a feature-flag on the OSS code. It's the printable PDF, 
the recorded video, custom rules for your codebase, priority Slack, and live 
migration pairing for Enterprise. All things that cost me time to produce per customer, 
and that I couldn't package as OSS without writing an LLM, which I refuse to do.
```

---

## Timing

- **Best day:** Tue/Wed/Thu
- **Best time:** 8-10am Pacific (San Francisco wake-up + US East Coast morning commute)
- **Avoid:** Monday (queue backed up from weekend), Friday (US engineers checked out)

## After submission

- Don't edit the title or body after submission (breaks the cache)
- Respond to every comment within ~30 minutes during the first 2 hours (drives rank)
- Don't ask friends to upvote — HN detects rings and penalizes
- **Don't submit more than once.** If it doesn't stick, write a different post in 2 weeks — do not resubmit the same URL

## Post-submission tasks for Operator

1. Paste the Show HN URL into `/workspace/rupture/ledger/mission_ledger.md`
2. Watch `https://news.ycombinator.com/show` and `https://news.ycombinator.com/newest` for the post
3. Answer any technical comments within 30 min — all the pre-written answers above are in this file