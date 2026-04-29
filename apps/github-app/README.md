# Rupture Migration Bot — GitHub App

The Rupture Migration Bot opens migration PRs on repositories that have **explicitly installed it**. Installation is consent. The bot will never open PRs on a repository that has not installed it.

## Install

Visit https://github.com/apps/rupture-migration-bot and click **Install**. Choose the repositories you want to migrate; defaults to "select repositories" (not all).

## What the bot does

On install, the bot scans the selected repositories for affected runtimes (Lambda Node.js / Amazon Linux 2 / Lambda Python) and queues at most one PR per repo per week, throttled to 5 PRs per installation per day. Each PR contains:

- The codemod diff (deterministic, hash-anchored).
- IaC patches for SAM, CDK (Python+TS), Terraform, Serverless, Packer, Ansible.
- A canary deploy plan referencing your existing CloudWatch alarms.
- A rollback script.
- A footer noting that **if your CI fails on this PR within 7 days, the corresponding paid Migration Pack purchase is auto-refunded**. Free-tier scans don't trigger any payment, so this only applies to Migration Pack customers.

## What the bot does NOT do

- It does **not** touch repositories that did not install the app.
- It does **not** push commits without opening a PR.
- It does **not** merge PRs.
- It does **not** access private code outside the installed repos.
- It does **not** add buyer code to the public corpus (`corpus/`); only public-repo benchmark data is aggregated, and even then only when its source repo is public.

## Opt-out for installed repos

Drop a file named `.no-rupture` (any contents) at the root of any repo. The bot honors it within 60 seconds.

## Abuse reporting

If the bot misbehaves on your repo, `POST` to `/abuse` with `{"repo": "owner/name"}` from `https://<worker-host>/abuse`. The bot will pause for that repo within 60 seconds. Maintainer-bot escalation also opens an internal issue tagged `abuse-report` for human review.

## Permissions requested

The minimum required to open a PR. See `permissions.md` for the precise list.
