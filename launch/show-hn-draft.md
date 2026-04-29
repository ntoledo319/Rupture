# Show HN draft

This is the body the agent submits at launch time. It is fully autonomous — no human pre-stakes comments, no reply playbook. The artifact carries the post.

## Title

```
Show HN: Rupture — three CLIs for AWS runtime deprecation deadlines (MIT)
```

## Submission URL

```
https://github.com/ntoledo319/Rupture
```

## Body

```
I built three CLIs that automate AWS migrations off deprecated runtimes:

- lambda-lifeline   Node.js 16/18/20 -> 22  (Apr 30, 2026)
- al2023-gate       Amazon Linux 2 -> AL2023 (Jun 30, 2026)
- python-pivot      Lambda Python 3.9/3.10/3.11 -> 3.12

Each kit does the same five things: scan the account, run mechanical
codemods (dry-run by default), patch IaC (SAM / CDK / Terraform / Serverless),
generate a staged canary deploy plan, and produce a tested rollback script.

What's interesting under the hood:

- Deterministic builds: same input -> byte-identical output (CI-gated).
- Hash-anchored audit reports: every PDF embeds SHA-256 of inputs and the
  rule-pack version, with a public verification URL.
- Property-based and mutation-tested codemods.
- Sigstore-signed releases with CycloneDX SBOMs.
- Public nightly benchmark across a curated corpus of real public IaC.

Free, MIT, on GitHub. Paid tiers (Audit PDF, Migration Pack, Org License,
Drift Watch) all self-serve via webhook -- no humans in the loop.

Repo:       https://github.com/ntoledo319/Rupture
Benchmark:  https://ntoledo319.github.io/Rupture/status/
Sample PDF: https://ntoledo319.github.io/Rupture/audit/
Calendar:   https://ntoledo319.github.io/Rupture/deprecations.ics
```

## Comment policy

The autonomous support bot may answer in-scope questions only, citing a doc URL on every reply. Out-of-scope questions are not answered (silence is the autonomy-compliant default). No human pre-stakes comments. No reply playbook.

## Timing

The agent surfaces a `[DECISION-7-launch-window]` block to the operator suggesting a Tuesday or Wednesday 8:00–10:00 PT submission. Operator clicks **Submit**; everything after that is automated.
