# EOLkits on GRACE

This is the GRACE-native deployment path for EOLkits paid fulfillment.

GRACE already owns the public static site as the `eolkits` satellite:

- id: `eolkits`
- kind: `static`
- domain: `eolkits.com`
- web root: `/var/www/eolkits`

Do not replace or duplicate that entry. This directory adds a second satellite,
`eolkits-api`, for paid API and webhook fulfillment only.

## Runtime Shape

- `eolkits.com` remains a static site served by host Caddy.
- selected API paths on `eolkits.com` are reverse-proxied to a GRACE-managed compose satellite.
- Local filesystem volume replaces Cloudflare R2.
- SQLite state under the API volume replaces Cloudflare KV for idempotency, jobs, verification records, and license keys.
- BackgroundTasks plus the inline runner replace Cloudflare Queues for the single-VPS GRACE shape.
- GRACE monitors and controls the API through the satellite plane.

## Apply On GRACE

On the VPS, use a separate site root:

```bash
sudo mkdir -p /home/ubuntu/sites/eolkits-api
sudo rsync -a --delete /path/to/Rupture/ /home/ubuntu/sites/eolkits-api/
cd /home/ubuntu/sites/eolkits-api
cp deploy/grace/docker-compose.eolkits-api.yml docker-compose.yml
```

Create `/home/ubuntu/sites/eolkits-api/.env.production` with:

```bash
# Required — the API fails closed at startup in ENVIRONMENT=production if any
# of STRIPE_KEY (live), STRIPE_WEBHOOK_SECRET, GITHUB_WEBHOOK_SECRET,
# GITHUB_APP_ID/PRIVATE_KEY, RESEND_API_KEY, or EOLKITS_INTERNAL_URL_SECRET
# are missing or use sandbox/dummy values.
STRIPE_KEY=sk_live_...                 # must be a live sk_live_/rk_live_ key
STRIPE_WEBHOOK_SECRET=whsec_...        # from the live Stripe webhook endpoint
GITHUB_APP_ID=...
GITHUB_APP_PRIVATE_KEY=...             # PEM contents (\n-escaped is fine)
GITHUB_APP_SLUG=...                    # the App's URL slug; powers the install link
GITHUB_WEBHOOK_SECRET=...
RESEND_API_KEY=...
EOLKITS_INTERNAL_URL_SECRET=...        # random 32+ byte secret for signed upload refs
PUBLIC_SITE_URL=https://eolkits.com
PUBLIC_API_URL=https://eolkits.com
EOLKITS_API_PORT=8120
```

Generate the internal-URL secret with `openssl rand -hex 32`.

**Redeploying an already-live host:** the existing `.env.production` already has
the Stripe/GitHub/Resend secrets — keep them. You only need to **append the two
vars introduced by the hardening** (`EOLKITS_INTERNAL_URL_SECRET` and
`GITHUB_APP_SLUG`); the API validates the full set on startup and will refuse to
boot if either is missing.

Start it:

```bash
sudo docker compose -p eolkits-api --env-file .env.production up -d --build
curl -sf http://127.0.0.1:8120/health
```

Insert `deploy/grace/Caddyfile.eolkits-api.block` inside the existing `eolkits.com, www.eolkits.com` block before the static `file_server`, then validate and reload:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
curl -sf https://eolkits.com/health
```

## GRACE Satellite Integration

Append `deploy/grace/satellites.eolkits-api.yaml` to `grace-backend/config/satellites.yaml`.

Add `deploy/grace/satellite-agent.eolkits-api.py.snippet` to the `SATELLITES` dict in GRACE's host-side satellite agent.

Then redeploy/restart the GRACE backend and satellite agent using GRACE's snapshot-first runbook. Afterward:

```bash
curl -sf https://graceai.love/api/v1/satellites
```

You should see both:

- `eolkits` for the static public site.
- `eolkits-api` for paid fulfillment.

## Public Endpoints

- `GET /health`
- `GET /status`
- `POST /upload/presign`
- `PUT /upload/{upload_id}`
- `GET /upload/{upload_id}`
- `GET /upload/report/{sha}`
- `POST /api/audit/checkout`
- `POST /api/pack/checkout`
- `POST /api/drift/checkout` (Drift Watch — subscription Checkout Session)
- `POST /api/events` (first-party funnel beacon; source/utm/kit/deadline/sku)
- `POST /webhook/stripe`
- `POST /webhook/github`
- `GET /pack/install`
- `GET /pack/setup` (GitHub App post-install Setup URL — persists installation→repo mapping)
- `GET /verify/{sha}` and `GET /api/verify/{sha}`
- `POST /support/ask`

## Cleanup

Once `https://eolkits.com/health` is live and Stripe/GitHub webhooks point to `https://eolkits.com/webhook/stripe` and `https://eolkits.com/webhook/github`, remove old Cloudflare Worker webhook URLs from provider dashboards. Keep `apps/worker/` only as historical/reference code until deleted in a follow-up cleanup.

