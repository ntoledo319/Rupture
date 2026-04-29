# Rupture GitHub App — Permissions

Minimum scopes required, justified.

## Repository permissions

| Permission | Level | Why |
|---|---|---|
| Contents | Read & Write | Branch creation and commit for migration PRs. |
| Pull requests | Read & Write | Opening, updating, and labelling PRs. |
| Metadata | Read | Required by GitHub for any installed app. |
| Checks | Read | Watching CI status to enforce the refund guarantee. |
| Issues | Read & Write | Open follow-up issues if a migration cannot be auto-applied. |

## Organization permissions

None.

## User permissions

None.

## Subscribed events

- `installation`
- `installation_repositories`
- `pull_request`
- `check_run`
- `check_suite`
- `push`

## Token lifetime

The app uses GitHub's standard installation tokens (1 hour). No long-lived PATs.

## Data handling

- Cloned content is held in the runner container for the duration of the migration job (typical: <60 seconds) and discarded.
- No buyer code is added to the public migration corpus; only public-repo benchmark data is aggregated.
- All access logs are retained for 30 days for abuse investigation, then purged.
