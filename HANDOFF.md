# MISSION HANDOFF: PLATFORM DEATHWATCH (RUPTURE)

**Status:** LIVE CHECKOUT ENABLED. REMAINING WORK IS DISTRIBUTION + RELEASE HARDENING.

## 1. Executive Summary
Rupture is a suite of three high-stakes migration kits targeting imminent AWS EOL and runtime deprecation deadlines (Amazon Linux 2, Node.js 20, Python 3.9-3.11). The project is structured as a monorepo containing production-ready CLI tools, a high-conversion landing page, and a distribution engine.

## 2. Deliverables
### Migration Kits (116 Tests Passing)
- **`lambda-lifeline`**: Node.js 20 -> 22 migration. (24 tests)
- **`al2023-gate`**: Amazon Linux 2 -> AL2023 migration. (48 tests)
- **`python-pivot`**: Python 3.9/3.10/3.11 -> 3.12 migration. (44 tests)
*Each kit includes: Scanner, Remapper, Audit Engine, IaC Updater, and Rollback logic.*

### Web Presence
- **Landing Page**: Located in `docs/index.html` (for GitHub Pages) and `apps/web/templates/`.
- **Demos**: Interactive SVG terminal animations for each kit located in `docs/demos/`.
- **Pricing**: Solo ($499), Team ($999), and Enterprise ($2,499) tiers mapped in `pricing.yml`.

### Launch Engine (`/launch`)
- **Show HN Draft**: Strategic posting guide and copy in `launch/show-hn-draft.md`.
- **SEO Blog Post**: 2,500-word authority post in `launch/blog-post.md`.
- **Thread Replies**: Ready-to-use templates for SO/GitHub/re:Post in `launch/thread-answers.md`.

## 3. Critical Operator Actions (Immediate)
1. **Infrastructure**: GitHub Pages is enabled on `main` + `/docs`.
2. **Commerce**: live Worker is deployed at `https://rupture-worker.rupture-kits.workers.dev`; audit checkout smoke test returns a live Stripe Checkout redirect.
3. **Distribution**:
    - **Tue/Wed (6-9 AM PT)**: Post the Show HN draft.
    - **SEO**: Publish the blog post to Dev.to/Medium.
    - **Direct Support**: Use the search queries in `launch/thread-answers.md` to find people currently struggling with these migrations and provide the templated help + kit mention.
4. **Release hardening**:
    - Wait for pushed GitHub Actions fixes to make determinism, ICS, benchmark, and status synthetic runs green.
    - Publish the first signed release and VS Code extension after CI is green.
    - Run one Migration Pack sandbox PR against `ntoledo319/rupture-sandbox`.

## 4. Revenue Trajectory
- **Goal**: $25,000 in 7 days.
- **Primary Funnel**: Show HN -> Source Repo -> Landing Page -> $499 Solo Kit.
- **Urgency Drivers**: The countdown timers on the landing page and kit outputs are linked to the April/June 2026 hard deadlines.

## 5. Maintenance
- **Kits**: Written in Python (al2023-gate, python-pivot) and Node.js (lambda-lifeline).
- **Updates**: Modify `rules/public/deprecations.yml` to update deadline dates or add new runtime warnings.

***

**DELETE THIS FILE ONCE SHOW HN, BENCHMARK, RELEASE, VS CODE PUBLISHING, AND THE SANDBOX MIGRATION PACK TEST ARE COMPLETE.**
