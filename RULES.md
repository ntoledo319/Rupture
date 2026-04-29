# Rupture — Public Rule Sources

> Every rule shipped in `rules/public/` is grounded in a publicly-published source. This file is the index of those sources. If a rule cannot cite a public source, it does not ship.

## AWS Lambda runtime deprecation

- AWS Lambda Runtimes — https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html
- Node.js Releases (upstream EOL schedule) — https://nodejs.org/en/about/previous-releases
- Python EOL schedule — https://devguide.python.org/versions/

## Amazon Linux 2 EOL

- Amazon Linux 2 FAQ — https://aws.amazon.com/amazon-linux-2/faqs/
- Comparing Amazon Linux 2 and Amazon Linux 2023 — https://docs.aws.amazon.com/linux/al2023/ug/compare-with-al2.html

## IMDSv1 / IMDSv2

- Use IMDSv2 — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html

## Native-module ABI breakage (Lambda)

- Lambda environment + native dependencies — https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html
- Node.js Native Addons — https://nodejs.org/api/addons.html

## OpenSSL 3 hash deprecations

- OpenSSL 3.0 migration guide — https://www.openssl.org/docs/man3.0/man7/migration_guide.html

## Citation rule

Every rule entry in `rules/public/*.yml` MUST include a `source_url` field pointing at a stable, public, primary source. PRs that add rules without `source_url` are rejected by CI. The CI check is enforced by `feed/publish.py` validation (the build fails if any rule lacks a source).
