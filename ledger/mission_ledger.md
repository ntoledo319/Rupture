# PLATFORM DEATHWATCH v3 — Mission Ledger

## Operator Context
- **Operator:** NinjaTech AI (Palo Alto) — personal LLC for this mission
- **LLC Name:** `[TBD — operator to confirm at Checkpoint 2]`
- **Stripe:** Active, connected to LLC business bank (operator-confirmed "all green")
- **GitHub:** `ntoledo319` — mission monorepo `ntoledo319/Rupture` (main)
- **Domain:** None purchased (Vercel free-tier subdomains, $0 budget)
- **Support email:** `[TBD — Checkpoint 2]`
- **Video:** Silent captioned screencast produced in VM
- **Posting:** Operator posts manually at Checkpoint 3

## Seed Budget
- **$0** — all infra on free tiers (GitHub, Vercel, Stripe)

## Timeline
| Time (UTC) | Event |
|---|---|
| 2026-04-28 07:54 | Mission start, workspace created |
| 2026-04-28 07:54 | Checkpoint 0 cleared |
| TBD | Phase 1 scan begins |
| TBD | Checkpoint 1 — target selection |
| TBD | Phase 2 kit build |
| TBD | Checkpoint 2 — kit approval |
| TBD | Phase 3 deploy + Stripe wiring |
| TBD | Checkpoint 3 — launch copy approval |
| TBD | Phase 4 launch |

## Rupture Candidates (Phase 1 complete — 2026-04-28 08:15 UTC)

### 🏆 A. AWS Lambda Node.js 20.x EOL — urgency 10/10
- Primary: https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html
- Phase 1 (patches stop): **Apr 30, 2026** (2 days)
- Phase 2 (block create): **Aug 31, 2026**
- Phase 3 (block update, HARD): **Sep 30, 2026**
- Gap: No integrated scan→codefix→test→deploy kit at SMB price
- Build: 8-14h, Medium complexity

### B. Amazon Linux 2 → AL2023 — urgency 8/10
- Primary: https://aws.amazon.com/amazon-linux-2/faqs/
- Deadline: **Jun 30, 2026** (63 days)
- Build: 14-24h, Medium-High (needs AWS creds for real AMI testing)

### C. Lambda Python 3.10 EOL — urgency 6/10
- Deadline: Oct 31, 2026 (186 days — too far out)
- Reserve as V2 kit

## Selected Target — Checkpoint 1 CLEARED 2026-04-28 08:22 UTC
**All three kits approved. Staged launch.**

- Kit 1: `lambda-lifeline` — Lambda Node.js 20 → 22 (launch Day 1-2)
- Kit 2: `al2023-gate` — Amazon Linux 2 → AL2023 (launch Day 4-5)
- Kit 3: `python-pivot` — Lambda Python 3.9/3.10 → 3.12 (launch Day 6-7)

**Umbrella brand:** Rupture Kits (rupture-kits.vercel.app)
**LLC:** [TBD at Checkpoint 2]
**Support email:** [TBD — using support@rupture-kits.dev as placeholder]

## Pricing (locked)
| Tier | Single Kit | Bundle (all 3) |
|---|---|---|
| Solo | $499 | $999 |
| Team | $999 | $1,999 |
| Enterprise | $2,499 | $4,997 |

## Target Math
- $25k goal = 5 Team bundles ($9,995) + 5 Solo bundles ($4,995) + 2 Enterprise bundles ($9,994) = **$25,959**
- Floor viability: 1 sale of any kind in 48h

## Kit
- Repo: _pending_
- Demo URL: _pending_
- Video: _pending_

## Stripe
- Product: _pending_
- Payment links: _pending_
- Tax enabled: _pending operator confirmation_

## Posts Published
_None yet._

## Revenue
| Tier | Price | Sales | Revenue |
|---|---|---|---|
| Solo | $499 | 0 | $0 |
| Team | $999 | 0 | $0 |
| Enterprise | $2,499 | 0 | $0 |
| **Total** | | **0** | **$0** |

## Traffic
_Populated after launch._

## Open Issues / Support
_None._

## Judgment Calls Log
- 2026-04-28: Skipping domain purchase → Vercel subdomain (consistent with $0 seed)
- 2026-04-28: Silent captioned screencast instead of voiceover (VM has no mic, operator time = 0)
- 2026-04-28: Using `ntoledo319/Rupture` as mission monorepo; each kit gets its own public repo
- 2026-04-28: Stripe payment link creation deferred to operator at Checkpoint 2 (security — no API keys in VM)