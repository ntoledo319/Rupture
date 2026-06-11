# Social — launch amplification

Post these the same morning the Show HN goes up. Thread the X post; LinkedIn stands alone.

## Voice notes

- X: tighter, more clipped. Mode 1 (conversational) for the punchy first post, Mode 4 (vulnerable) for the reply. Lowercase is fine on X if the rhythm wants it; standard capitalization is also fine. Match what feels right in the moment.
- LinkedIn: Mode 9 (analytical) primary, no swearing, standard capitalization throughout. Slightly more formal, but never corporate.
- The product is not the headline anywhere. The deadline is.

---

## X — thread (2 posts)

### Post 1

```
EOLkits is live.

CLIs for the AWS deprecation deadlines that break prod:

– al2023-gate (Amazon Linux 2 → AL2023, Jun 30)
– python-pivot (Lambda Python 3.9-3.11 → 3.12)
– lambda-lifeline (nodejs20.x → 22 — Phase 1 passed Apr 30; cliff Sep 30)

MIT. Deterministic, CI-gated builds. Property- and mutation-tested.

github.com/ntoledo319/EOLkits
```

### Post 2 (reply to Post 1)

```
Each kit: scan, codemod, IaC patch, canary plan, rollback. Default is dry-run. Free GitHub Action runs the dry-run pass on PRs and comments findings.

Built it solo because I kept getting the same deprecation emails from AWS every six months and there was no end-to-end tool. So I made one. Three.

Show HN posting later this morning.
```

### Post 3 (reply to Post 2, posted only after Show HN goes up)

```
HN: [paste the news.ycombinator.com URL]

If you've ever done one of these migrations and the kit missed something on your codebase, that's the most useful thing anyone can tell me right now.
```

---

## LinkedIn — single post

```
After 14 months of building, EOLkits is live.

EOLkits is three open-source CLIs that automate AWS runtime migrations off the deprecation deadlines breaking production this year:

– al2023-gate — Amazon Linux 2 → AL2023 (Jun 30, 2026 — live deadline)
– python-pivot — Lambda Python 3.9 / 3.10 / 3.11 → 3.12 (rolling EOL waves)
– lambda-lifeline — Node.js 16 / 18 / 20 → 22 (Phase 1 passed Apr 30; Phase 3 cliff Sep 30)

Each kit scans your account, runs codemods (dry-run by default), patches IaC across SAM / CDK / Terraform / Serverless / Packer / Ansible, generates a staged canary deploy plan, and produces a tested rollback script. The free GitHub Action runs the dry-run pass on every PR and comments findings.

The pieces I cared about most: deterministic, CI-gated builds, hash-anchored audit PDFs, property- and mutation-tested codemods, Sigstore-signed releases. If you've ever been the engineer paged at 2 a.m. because a runtime block landed mid-deploy, you'll recognize why every one of those mattered.

MIT licensed. Solo built. Repo open.

github.com/ntoledo319/EOLkits
```

---

## Posting order

1. **T-30 min before HN submission**: post X Post 1 + 2 (the thread). Post LinkedIn.
2. **T+0**: submit Show HN.
3. **T+5 min**: reply to your own X thread with Post 3 carrying the HN URL. Do NOT edit Posts 1 or 2 to add the link — the X algorithm penalizes link edits.
4. **First 6 hours**: stay on the HN thread. Do not boost the X post in any group chat. Organic only.

## What not to post

- No "we're so excited to share." The work is the announcement.
- No "after months of hard work" — version of the same thing.
- No screenshots of the GitHub stars graph. Ever.
- No tagging influencers. They'll see it or they won't.
