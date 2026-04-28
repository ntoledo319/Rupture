# CHECKPOINT 2 — Kit Fabrication Complete

**Time:** 2026-04-28, ~3h elapsed from mission start
**Status:** 3 kits fully built, tested, pushed to GitHub, landing page live

## Deliverables

### Kits (all in `ntoledo319/Rupture/kits/`)

| Kit | Deadline | Language | Commands | Tests | Status |
|---|---|---|---|---|---|
| lambda-lifeline  | 2026-04-30 (2 days) | Node.js | 8 | 24 | ✅ Ready |
| al2023-gate      | 2026-06-30 (63 days) | Python | 6 | 48 | ✅ Ready |
| python-pivot     | 2026-10-31 (186 days, with 3.9 already past) | Python | 6 | 44 | ✅ Ready |

**Total: 116 tests, 0 failures. All three kits work 100% offline in fixture mode.**

### GitHub
- Repo: https://github.com/ntoledo319/Rupture
- Branch: main
- Latest commits: 2 (lambda-lifeline, then al2023-gate + python-pivot + umbrella README)
- Monorepo layout: `/kits/{lambda-lifeline,al2023-gate,python-pivot}/`
- All code MIT-licensed

### Landing page
- Preview URL: https://013eq.app.super.myninja.ai
- Features: hero, 3-kit cards (lambda-lifeline marked urgent), how-it-works flow (5 steps), pricing grid (Solo/Team/Enterprise), bundle card, FAQ (7 items), footer
- Tech: hand-written HTML + CSS, dark mode native, fully responsive, no JS framework, no CDN
- Ready for Vercel deploy (or S3 static hosting via the `deploy` tool)

### Pricing (decided pre-operator)
- Solo $499 / Team $999 / Enterprise $2,499 per kit
- **Bundle all 3**: Solo $999 / Team $1,999 / Enterprise $4,997
- Best bundle discount: $2,500 off Enterprise

## Revenue math check
To hit $25K in 7 days:
- 50 × Solo single kits ($499) = $24,950  (feasible if we get 1 Show HN hit + 1 Reddit hit)
- OR 25 × Team single kits ($999) = $24,975
- OR 5 × Team bundles ($1,999) + 20 × Solo ($499) = $9,995 + $9,980 = $19,975 → need ~12 more Solos
- OR 10 × Enterprise singles ($2,499) = $24,990
- OR 5 × Enterprise bundles ($4,997) = $24,985  ← fewest buyers needed

The Enterprise bundle is the highest-leverage path. Landing page de-emphasizes this (Team is featured) because that's the honest "most popular" pick for inbound traffic, but Enterprise bundle is where we close $25K with 5 buyers.

## What's decided vs what still needs operator input

**Decided (trust-my-judgment calls):**
- 3 kits instead of 1 (operator: "do em all")
- Monorepo instead of separate repos (bot token can't create repos)
- Node.js 20 EOL stays top urgency (Apr 30 = 2 days out)
- Canary stages 5/25/50/100 with CloudWatch alarm gate
- Python-pivot Python 3.12 as target (not 3.13 — Lambda has it but maturity)
- AL2023 remap table focused on high-frequency breakage, not exhaustive

**Open for operator at Checkpoint 3 (Launch):**
- Show HN title + body (will draft for approval)
- Reddit post in r/aws (will draft for approval)
- Twitter thread (will draft for approval)
- Which Stripe price IDs to wire to the checkout buttons
- Domain name (suggested: rupture-kits.com, rupturekits.com, or stay on 013eq.app.super.myninja.ai for launch)
- Whether to deploy landing page now via `deploy` tool or keep serving locally

## Ready for Checkpoint 2 sign-off
