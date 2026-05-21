# Partner outreach

Three variants for three relationships. Pick the one that matches the target. Fill the bracketed fields and send.

## Voice notes

- Cold strangers: zero swearing, zero slang, Mode 9 (analytical) plus a thin layer of Mode 2 (supportive) at the close. Standard capitalization. The wall is sky-high — you have one paragraph to feel human.
- Warm contacts: drop the formality, keep the brevity. One mild swear is okay if it lands. Standard capitalization.
- Post-install: warmest. Mode 2 + Mode 9. Lead with thanks. Two clear asks. No upsell.
- Across all three: the deadline is the news, not the product. Lead with the thing that breaks. Link is a footer, not a CTA.

---

## Variant 1 — COLD MAINTAINER (AL2023, live deadline)

For someone you don't know with a public repo running Amazon Linux 2 in launch templates, AMIs, EKS node groups, or Beanstalk platforms. Do not send if you don't have a specific finding to lead with.

```
Subject: Amazon Linux 2 EOL Jun 30 — auto-migration PR for [repo]

[name],

Solo dev behind Rupture here. Running the open scanner against public repos and saw [repo] still pins Amazon Linux 2 in [specific file, e.g. "the EKS node group in eks/cluster.tf" or "the Packer template at packer/api.json"]. Jun 30 is EOL — after that, no patches, no new AMIs, anything depending on AL2 in CI starts breaking when the base images go.

I built a kit that scans the repo, runs the package-name remap (yum→dnf, deprecated packages, replacements), patches the IaC (Terraform / CloudFormation / Packer / Ansible / cloud-init), and opens a PR with a tested rollback path. MIT, mutation-tested at 80%+, deterministic builds.

If you want it run against [repo]: install at github.com/apps/rupture-migration-bot. One PR per repo per week, max. Free tier never charges. Drop a `.no-rupture` file at the repo root and the bot stops touching it within 60 seconds.

Deadline shows up in production at the worst possible moment. Thought you should know.

github.com/ntoledo319/Rupture

— Nicholas Toledo
```

> **Post-deadline cleanup variant:** the same template works for `lambda-lifeline` (Node 20 → 22, Phase 1 already passed Apr 30) — swap the subject to `nodejs20.x cleanup before Sep 30 cliff — auto-migration PR for [repo]` and update the body's deadline framing to "Phase 3 (Sep 30) is the hard cliff." Don't lead with Apr 30 — that's history; lead with Sep 30.

## Variant 2 — WARM CONTACT (waitlist, network, mutuals)

For someone who already opted in or who you know personally. Asking for a real-world test before the public launch.

```
Subject: Rupture is live — want me to run it on [repo / your stack]?

[name] —

Soft-launched Rupture this week. Three CLIs for the AWS runtime deprecations breaking prod this year (AL2 Jun 30, Python 3.x waves, plus Node 20 cleanup before the Sep 30 cliff). I think [repo / your team's stack] would be a clean target — saw [specific thing about their setup, e.g. "the SAM templates in [repo] still pin nodejs20.x" or "your team mentioned Python 3.10 functions back in [context]"].

Looking for two or three real-world end-to-end runs before I post to HN on Tuesday morning. The deal: install the GitHub App at github.com/apps/rupture-migration-bot, pick the repos you want it to touch, it opens one PR per repo with the migration applied. Free, MIT, dry-run by default, opt-out by dropping a `.no-rupture` file.

If you're up for being one of the launch-day case studies, I'll comp the Migration Pack tier as a thank-you and link [repo / your company] on the launch page if you want the credit. Total opt-out also fine — happy to just have the test run.

Either way, deadline's real and shows up at the worst time.

github.com/ntoledo319/Rupture

— Nikki
```

## Variant 3 — POST-INSTALL (PR merged)

For someone who installed the bot and merged the PR. Two asks, both opt-out, no upsell.

```
Subject: Rupture PR merged in [repo] — quick favor?

[name],

Saw [repo] merged the rupture-bot PR. That's the first real-world end-to-end I've shipped on this thing — massive thanks for taking the leap.

Two asks, both fully optional:

1. If anything in the PR was off — codemod fired wrong, IaC pattern I missed, copy I should rewrite, anything — I want to know. Bug reports help me more than positive reviews right now.

2. If the migration went clean and CI's still green a week from now, would you be okay with me linking [repo / company] on the Rupture launch page as a real-world install? Just "Used in production at [company]" with a link. Happy to draft the line and run it past you before it goes live. If you'd rather skip the public credit, no follow-up — the PR itself was the gift.

Either way, thanks for being one of the first.

github.com/ntoledo319/Rupture

— Nicholas
```

## Sending notes

- Find the maintainer's public email through GitHub's commit metadata or their profile. Don't scrape, don't guess.
- One outreach per maintainer per repo. If they don't reply, don't follow up.
- Do not BCC. Do not template-blast. Each send needs the bracketed fields filled with something true and specific.
- For org-owned repos, prefer a maintainer you can identify as an active human; never send to a `*-noreply` or bot address.
- Subject line is the deadline + repo. Body has the kit. Footer has the link. That's the order.
