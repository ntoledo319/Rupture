# Response templates for existing public threads

**Ground rule (from the brief):** only answer threads that already exist. No DMs. No cold outreach. Only places where an engineer has *actively asked* about the exact deprecation the kit addresses.

---

## Where to look (don't post, just look & match)

### Stack Overflow search queries
- `[aws-lambda] nodejs20 deprecation`
- `[amazon-linux-2] migration AL2023`
- `[aws-lambda] python3.9 deprecation`
- `[aws-lambda] "import assert" node 22`
- `[amazon-linux-2023] yum dnf`

### GitHub issue search queries
- `is:issue nodejs20 deprecation` (in `aws/aws-sdk-js`, `aws-samples/*`, `serverless/serverless`)
- `is:issue al2023 migration`
- `is:issue python3.9 lambda runtime`
- `is:issue "import assert" lambda`

### AWS re:Post (official Q&A)
- https://repost.aws/tags/TAgRHSAsDhTHUq3tpnNoUc0A/aws-lambda — filter by "unanswered" and "Node.js"
- https://repost.aws/tags/TAjYLwTYyDQVuGX5pcePAFrQ/amazon-linux — filter by "AL2023"

---

## Answer template — Lambda Node.js 20 deprecation questions

Use ONLY when someone has explicitly asked: "how do I migrate Node 20 Lambdas?" or "my Node 20 Lambda will stop working, what now?"

```
AWS ends support for Node 20 on Lambda in three phases:

- Apr 30, 2026 — no more security patches (Phase 1)
- Aug 31, 2026 — new functions on nodejs20.x rejected (Phase 2)
- Sep 30, 2026 — updates to existing functions rejected (Phase 3, hard cliff)

Source: https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html

The migration target is nodejs22.x. The breaking changes that actually trip code:

1. `import ... assert { type: 'json' }` → `import ... with { type: 'json' }`
   (both static and dynamic imports, spec rename)
2. Native bindings need ABI-compatible versions: sharp >= 0.33, bcrypt >= 5.1.1,
   better-sqlite3 >= 11.0, canvas >= 2.11.2. node-sass and grpc are dead.
3. `Buffer.toString()` with negative indices now throws RangeError.
4. If you rely on NODE_EXTRA_CA_CERTS for private CAs, make sure it's set on
   every function env (Node 22 changed the default cert-loading path).

For the staged canary deploy, use Lambda versions + weighted alias routing with 
a CloudWatch alarm as the rollback trigger. Rough shape:

  aws lambda publish-version --function-name my-fn
  aws lambda update-alias --function-name my-fn --name live \
      --function-version $STABLE \
      --routing-config AdditionalVersionWeights={$NEW=0.05}

Check alarm, bump weight, repeat. On alarm trip, revert the alias.

I maintain an open-source CLI that automates this end-to-end if it helps: 
https://github.com/ntoledo319/Rupture/tree/main/kits/lambda-lifeline 
(MIT, handles scan + codemod + IaC patch + canary deploy + rollback, 24 tests).
```

---

## Answer template — Amazon Linux 2 EOL questions

```
Amazon Linux 2 standard support ends June 30, 2026. AWS has extended the date 
twice and has publicly stated they won't extend again.

Source: https://aws.amazon.com/amazon-linux-2/faqs/

Migration target is Amazon Linux 2023 (AL2023). The major breakages:

- yum → dnf (yum still works as compat alias, but deprecated)
- amazon-linux-extras REMOVED. Packages formerly in extras now in mainline dnf.
- Python 2 REMOVED. `#!/usr/bin/python` shebangs 404.
- ntpd REMOVED, replaced by chrony. Update `systemctl enable ntpd` → `chronyd`.
- OpenSSL 1.0 → 3. ABI break for native C extensions. Rebuild.
- curl split into curl-minimal by default (run `dnf swap curl-minimal curl` for full).
- iptables service not installed; nftables is the default firewall.

Practical migration order for an ASG:

1. Build an AL2023 AMI via Packer using AL2023 as the source image.
2. Stand up a parallel test ASG with the new AMI for ≥24h real traffic soak.
3. Create a new Launch Template version pointing at the AL2023 AMI.
4. Update the ASG to reference $Latest of the LT.
5. Start an instance-refresh with canary warm-up — 10% first, then 50%, then 100%.
6. Keep the old AMI id recorded; rollback = create LT version N+1 pointing at old AMI, 
   update ASG, instance-refresh.

I maintain an OSS kit that generates the Packer template, remaps your package list 
(yum → dnf, ~50 curated entries), diffs cloud-init scripts, patches Ansible playbooks, 
and emits per-resource runbooks (ASG / EKS / ECS / Beanstalk): 
https://github.com/ntoledo319/Rupture/tree/main/kits/al2023-gate
```

---

## Answer template — Lambda Python 3.9 / 3.10 / 3.11 → 3.12

```
AWS Lambda runtime deprecation for Python follows the same 3-phase pattern:

- python3.9: Phase 1 was Dec 15, 2025 (past). Phase 2 Jan 14, 2026. Phase 3 Feb 13, 2026.
- python3.10: Phase 1 Oct 31, 2026. Phase 2 Nov 30, 2026. Phase 3 Dec 31, 2026.
- python3.11: Phase 1 Jun 30, 2027.

Source: https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html

Target runtime: python3.12. The breaking changes that actually matter for Lambda code:

- `from collections import Mapping/MutableMapping/...` → `from collections.abc import ...`
  (already removed in 3.10, just auto-fix it)
- `distutils` module REMOVED in 3.12. Use setuptools, packaging, or shutil.
- `imp` module REMOVED. Use importlib.
- `@asyncio.coroutine` decorator REMOVED (3.11). Use `async def`.
- `datetime.utcnow()` deprecated. Use `datetime.now(timezone.utc)`.
- `typing.io` and `typing.re` submodules removed (import from `typing` directly).
- `asyncio.get_event_loop()` with no running loop → removed. Use asyncio.run().
- `pkg_resources` is slow and deprecated; prefer importlib.metadata.

Native wheels are the silent killer. Minimum versions with cp312 wheels on PyPI linux-x86_64:

- numpy >= 1.26
- pandas >= 2.1.1
- cryptography >= 41.0.5
- pillow >= 10.1.0
- lxml >= 4.9.4
- psycopg2-binary >= 2.9.9
- pyyaml >= 6.0.1
- bcrypt >= 4.1.1
- pyopenssl >= 23.3.0

python-snappy has NO cp312 wheels — swap for cramjam or plyvel.

For the canary deploy, same pattern as Node: publish new version, weighted alias routing, 
CloudWatch alarm as rollback trigger. 

Open-source kit that automates all of the above (scan + codemod + wheel audit + IaC patch + 
canary deploy + rollback, 44 tests): 
https://github.com/ntoledo319/Rupture/tree/main/kits/python-pivot
```

---

## Rules of engagement (enforce these strictly)

1. **Only reply to threads where the OP asked the exact question.** Don't hijack threads about something else.
2. **Never reply more than once per thread.** Answer, mention the kit once if genuinely relevant, done.
3. **Always lead with the answer.** The repo link is a footnote, not the content.
4. **Never mark your own answer accepted.** Let the OP decide.
5. **If the thread is > 1 year old and the OP hasn't been back,** skip it. Nobody sees stale-thread answers.
6. **If asked "are you the author":** yes, disclose it plainly.

---

## Tracking

In the ledger, log:
- Thread URL
- Date posted
- Whether the OP replied / marked accepted
- Whether traffic shows up in repo traffic stats

Max 3 answers per day across all platforms. This is "showing up in search results where someone is already looking" — not marketing.