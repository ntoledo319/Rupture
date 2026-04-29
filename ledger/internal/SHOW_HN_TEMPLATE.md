# Show HN Submission Template

## Title

Show HN: Rupture – Open-source AWS deprecation scanner with auto-migration PRs

## URL

https://ntoledo319.github.io/Rupture

## Text (for discussion)

Rupture is an open-source toolkit for AWS infrastructure deprecation scanning. It reads your SAM/CDK/Terraform/CloudFormation and:

- Detects deprecated Lambda runtimes (Node.js 20, Python 3.9-3.11)
- Detects Amazon Linux 2 usage
- Applies mechanical codemods (dry-run by default)
- Opens automated PRs (optional, opt-in)
- Provides deterministic, hash-anchored audit reports

The CLI is MIT licensed and free. Revenue comes from:
- $299+ Audit PDFs (hash-verified)
- $1,499 Migration Pack (auto-PR + refund guarantee)
- $14,999/yr Org License
- $19/mo Drift Watch subscription

Built with $0 seed: Cloudflare Workers (free), Stripe (revenue-based), GitHub Actions, GitHub Pages. No paid services until revenue lands.

Key technical decisions:
- Deterministic builds (same input = same output, bit-for-bit)
- 80%+ mutation test score required for release
- Sigstore signing for binaries
- No human in fulfillment loops (auto-refund on CI failure)

Repo: https://github.com/ntoledo319/Rupture

Would love feedback on:
1. Would you use this?
2. Is the pricing model fair?
3. What other AWS deprecations should we track?

---

## Launch Checklist

- [ ] Stripe in live mode
- [ ] All webhook endpoints tested
- [ ] Auto-refund logic verified
- [ ] GitHub App installed on test repo
- [ ] PR flow tested end-to-end
- [ ] Audit PDF generation tested
- [ ] Support bot responding
- [ ] Status page green
- [ ] Documentation complete
- [ ] Legal docs linked from footer

## Timing

Best time to post: Tuesday-Thursday, 9-11am PT

## Follow-up Comments

Be ready to respond quickly to questions about:
- How codemods work (safety, dry-run)
- Why this vs existing tools (comparison table ready)
- Pricing justification (market rate for audit services)
- Security (no credentials stored, open source)
