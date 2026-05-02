#!/usr/bin/env bash
# Wire GitHub App credentials into the Cloudflare worker + runner secrets.
#
# Usage:
#   ./setup_github_app.sh \
#     --app-id 123456 \
#     --private-key-pem /path/to/rupture-bot.private-key.pem \
#     --webhook-secret 'super-random-string'
#
# Or interactively:
#   ./setup_github_app.sh
#
# Requires: wrangler (npm i -g wrangler), GitHub App already created from
# apps/github-app/manifest.json (the /pack/install endpoint generates the URL).

set -euo pipefail

APP_ID=""
PRIVATE_KEY_PATH=""
WEBHOOK_SECRET=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --app-id) APP_ID="$2"; shift 2;;
    --private-key-pem) PRIVATE_KEY_PATH="$2"; shift 2;;
    --webhook-secret) WEBHOOK_SECRET="$2"; shift 2;;
    -h|--help)
      sed -n '2,15p' "$0"; exit 0;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

prompt() {
  local var="$1" label="$2" silent="${3:-no}"
  local current; current="$(eval echo \${$var})"
  if [[ -z "$current" ]]; then
    if [[ "$silent" == "yes" ]]; then
      read -r -s -p "$label: " current; echo
    else
      read -r -p "$label: " current
    fi
    eval "$var=\"$current\""
  fi
}

prompt APP_ID "GITHUB_APP_ID (numeric)"
prompt PRIVATE_KEY_PATH "Path to GitHub App private key (.pem)"
prompt WEBHOOK_SECRET "GITHUB_WEBHOOK_SECRET" yes

if [[ ! -f "$PRIVATE_KEY_PATH" ]]; then
  echo "Private key not found at: $PRIVATE_KEY_PATH" >&2
  exit 1
fi

PRIVATE_KEY_CONTENTS="$(cat "$PRIVATE_KEY_PATH")"

if ! command -v wrangler >/dev/null 2>&1; then
  echo "wrangler CLI not on PATH. Install: npm i -g wrangler" >&2
  exit 1
fi

WORKER_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$WORKER_DIR"

echo "==> Pushing GITHUB_APP_ID"
echo -n "$APP_ID" | wrangler secret put GITHUB_APP_ID

echo "==> Pushing GITHUB_APP_PRIVATE_KEY"
printf '%s' "$PRIVATE_KEY_CONTENTS" | wrangler secret put GITHUB_APP_PRIVATE_KEY

echo "==> Pushing GITHUB_WEBHOOK_SECRET"
echo -n "$WEBHOOK_SECRET" | wrangler secret put GITHUB_WEBHOOK_SECRET

cat <<EOF

Cloudflare worker secrets installed.

Next: mirror these into the runner environment (where the migration_pr job runs):
  export GITHUB_APP_ID='$APP_ID'
  export GITHUB_APP_PRIVATE_KEY="\$(cat $PRIVATE_KEY_PATH)"

Verify:
  curl -fsS https://rupture-worker.rupture-kits.workers.dev/health
  # Trigger a test webhook delivery from the GitHub App settings page.
EOF
