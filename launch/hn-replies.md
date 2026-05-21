# HN reply playbook

Pre-written answers to the questions HN will absolutely ask. Lead with the answer, no preamble. Reply once per top-level comment. Stop unless someone asks.

## Voice notes

- Mode 9 (analytical) throughout. Mode 4 (vulnerable) only if someone asks something genuinely personal about why you built it.
- No defending the product. Concede what's true; redirect on what isn't.
- "I think" is fine and used. "I appreciate" is not. "Great question" is not.
- No exclamation marks in any reply. Period.

---

## "Why not Renovate / Dependabot?"

```
Renovate updates package.json versions. The runtime upgrade also lives in IaC (SAM Runtime: nodejs20.x, CDK lambda.Runtime.NODEJS_20_X, Terraform runtime = "nodejs20.x") and in source code (the import-assertion → import-attribute syntax change is a hard parse error in Node 22, not a dep bump). Rupture is the part that handles those — the codemod plus the IaC patch plus the deploy/rollback. It's complementary to Renovate, not a replacement.
```

## "AWS already emails you about this. Why a tool?"

```
The email tells you the runtime is deprecated. It doesn't enumerate the functions, doesn't generate the codemod, doesn't patch the IaC, doesn't stage the canary, doesn't write the rollback. The work between "you got the email" and "everything is migrated and CI is green" is the entire job.
```

## "Why three CLIs and not one?"

```
Different runtimes, different breakage surfaces, different IaC patterns, different deadlines. Bundling them into one CLI would mean every user installs four times more code than they need. Each kit is a few hundred lines of focused work; you only install the one that matches your deadline. The shared pieces (canary executor, rollback executor, audit PDF generator) live in a common library the kits import.
```

## "Open source AND paid tiers — how does that work?"

```
The CLIs are MIT and complete. You can run scan / codemod / iac / deploy / rollback offline against fixtures or live against AWS, no payment required, no feature-gated nags. The paid tiers add things you'd otherwise build yourself: a printable hash-anchored audit PDF for the change-management folks, a fleet drift watcher, an org-license terms doc, and the migration-pack PRs against private repos with a 7-day CI-failure auto-refund. If your shop never wanted any of those, the free tier is the whole product.
```

## "Mutation testing at 80% — what tool?"

```
mutmut for the Python kits, Stryker for lambda-lifeline. The runs are in CI, gated, and the score thresholds are checked on every PR. The current weekly mutation run is signed off the main branch. Result: https://github.com/ntoledo319/Rupture/actions/workflows/mutation.yml
```

## "What's the codemod tech?"

```
For lambda-lifeline (the JS/TS kit): Babel for the AST + a small custom transformer per rule, because the rules are narrow enough that I wanted full control over the diff and didn't want jscodeshift's traversal opinions. For the Python kits: libcst, same reason. Every rule has a property test (random valid input → valid output) and a snapshot test (known input → exact diff). The diff is what I'd write by hand.
```

## "Have you used this in production?"

```
On my own infra, yes. The first real outside install opened its first PR yesterday — the sandbox repo end-to-end test merged the runtime upgrade with no manual edits. That's the proof I had before posting. I'd love more real-world runs and the GitHub App is the way to give me one.
```

## "How do you handle the case where the codemod is wrong?"

```
Three layers:

1. Default is dry-run. Nothing writes to your tree without --apply.
2. The PR opens on a branch, never to main.
3. The Migration Pack tier auto-refunds if CI fails on the bot's PR within 7 days, no human in the loop.

If you find a case the codemod gets wrong on free tier, file an issue and I'll cut a release with the rule fix. The rule pack is versioned so you can pin to a known-good rev if needed.
```

## "Why should I trust a solo dev's tool with my AWS account?"

```
You shouldn't, blindly. Three things you can verify before pointing it at your account:

1. Run it offline. Every kit works against fixtures with no AWS creds. You can see exactly what diff it would produce on a synthetic repo before letting it near yours.
2. Run it dry. Default is --dry-run on every command. It prints the diff, writes nothing.
3. Read the rules. The codemod rule files are small and human-readable. The IaC patcher patterns are visible YAML/regex pairs. There's nothing magic.

The kits don't take AWS credentials from anywhere except the standard credential chain. There's no telemetry. The audit PDF generator runs locally.
```

## "Can I see the bot's actual PR diff?"

```
Yes — here's the sandbox end-to-end run from yesterday: [paste actual sandbox PR URL when posting]

The two-file diff is the entire output: template.yaml runtime bumped (twice), processor.mjs assert→with rewritten. Branch name, commit message, PR body, and labels are all in the screenshot.
```

## "Is the audit PDF actually verifiable or is the SHA-256 a vibe?"

```
Verifiable. Every PDF embeds the SHA-256 of the input artifact, the rule-pack version SHA, the kit version, and a verification URL hosted at ntoledo319.github.io/Rupture/audit/verify. You paste the embedded hash into the verify page; it returns either a match (bytes-identical) or a mismatch with the diff. If the page is down, the same check is reproducible offline with shasum -a 256 against the inputs the PDF documents.
```

## "Why post this now and not before April 30?"

```
Honest answer: I had the kits done in February. Posted nothing. Life got in the way and the original launch window in early May passed. The Apr 30 Phase 1 EOL for Node 20 is now history — that's fair criticism and I'd rather own it than dance around it.

What's still live: Amazon Linux 2 EOL is Jun 30 (40 days from this post). Lambda Python 3.9/3.10/3.11 are still in their EOL waves. And the Node 20 hard cliff is actually Sep 30 — Phase 3, when AWS blocks updates to existing functions — so lambda-lifeline is still useful as cleanup if you have functions still on nodejs20.x. The kits don't expire when one of their deadlines does. But the framing on the README and this post leads with what's still ahead of us, not what's behind.
```

## If someone is hostile

Don't argue. One reply, fact-based, no defense. If the comment is clearly trolling, don't reply at all. Silence is fine. The thread is not your job to win.

```
Fair point on [specific thing]. The way it currently handles that is [factual description]. If you'd prefer it handle [X] differently, the rules file is at [path] and PRs are open.
```

## If someone offers help

Take it.

```
That'd actually be useful. The rule for [X] is the one I've been least sure about. If you're up for it, the file's at [path]. Happy to talk through the constraints over a call or just iterate in the PR.
```

## Hard rules for the thread

- One reply per top-level comment, ever.
- Do not edit your replies after posting unless to fix a typo. HN flags edits.
- Do not link to the Migration Pack purchase page in any reply.
- Do not say "thanks for the kind words." Say nothing or say what's next.
- After 6 hours, stop responding to new comments unless they're substantive bug reports.
