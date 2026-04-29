/**
 * White-label partner endpoints.
 *
 * Partners run audits under their own brand. Stripe Connect (Express
 * accounts) handles the rev split (70% partner / 30% Rupture). Logo
 * attribution is gated by DNS TXT verification of the partner's domain
 * to prevent impersonation.
 */

import type { Env } from './index';

interface PartnerRecord {
  slug: string;
  email: string;
  display_name: string;
  domain: string;
  domain_verified: boolean;
  stripe_account_id: string | null;
  logo_url: string | null;
  created_at: string;
}

const PARTNERS_KV_PREFIX = 'partner:';
const REV_SHARE_PARTNER = 0.7;

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

export async function partnerSignup(
  request: Request,
  env: Env
): Promise<Response> {
  const body = (await request.json()) as Partial<PartnerRecord>;
  if (!body.email || !body.display_name || !body.domain) {
    return jsonResponse(
      { error: 'email, display_name, domain required' },
      400
    );
  }

  const slug = (body.display_name || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .slice(0, 32);

  const existing = await env.IDEMPOTENCY.get(`${PARTNERS_KV_PREFIX}${slug}`);
  if (existing) {
    return jsonResponse({ error: 'partner_slug_taken', slug }, 409);
  }

  const stripeAccountId = await createStripeConnectAccount(env, body.email);
  const record: PartnerRecord = {
    slug,
    email: body.email,
    display_name: body.display_name,
    domain: body.domain,
    domain_verified: false,
    stripe_account_id: stripeAccountId,
    logo_url: null,
    created_at: new Date().toISOString(),
  };

  await env.IDEMPOTENCY.put(
    `${PARTNERS_KV_PREFIX}${slug}`,
    JSON.stringify(record)
  );

  const onboardingUrl = await getStripeAccountLink(env, stripeAccountId);

  return jsonResponse({
    slug,
    onboarding_url: onboardingUrl,
    verification_record: {
      type: 'TXT',
      host: '_rupture.' + body.domain,
      value: `rupture-verification=${slug}`,
    },
  });
}

export async function partnerVerifyDomain(
  request: Request,
  env: Env
): Promise<Response> {
  const url = new URL(request.url);
  const slug = url.pathname.split('/').pop();
  if (!slug) return jsonResponse({ error: 'slug required' }, 400);

  const record = (await env.IDEMPOTENCY.get(
    `${PARTNERS_KV_PREFIX}${slug}`,
    'json'
  )) as PartnerRecord | null;
  if (!record) return jsonResponse({ error: 'partner not found' }, 404);

  // Best-effort DNS-over-HTTPS lookup via Cloudflare 1.1.1.1.
  const dohUrl = `https://cloudflare-dns.com/dns-query?name=_rupture.${record.domain}&type=TXT`;
  const dnsResp = await fetch(dohUrl, {
    headers: { Accept: 'application/dns-json' },
  });
  const dnsData = (await dnsResp.json()) as {
    Answer?: Array<{ data: string }>;
  };
  const expected = `rupture-verification=${slug}`;
  const found = (dnsData.Answer ?? []).some((a) => a.data.includes(expected));

  record.domain_verified = found;
  await env.IDEMPOTENCY.put(
    `${PARTNERS_KV_PREFIX}${slug}`,
    JSON.stringify(record)
  );

  return jsonResponse({ slug, verified: found });
}

export async function partnerAudit(
  request: Request,
  env: Env
): Promise<Response> {
  const url = new URL(request.url);
  const parts = url.pathname.split('/').filter(Boolean); // ['partners', '<slug>', 'audit']
  const slug = parts[1];
  if (!slug) return jsonResponse({ error: 'slug required' }, 400);

  const record = (await env.IDEMPOTENCY.get(
    `${PARTNERS_KV_PREFIX}${slug}`,
    'json'
  )) as PartnerRecord | null;
  if (!record) return jsonResponse({ error: 'partner not found' }, 404);

  const body = (await request.json()) as {
    buyer_email: string;
    upload_url: string;
    stripe_session_id: string;
  };

  await env.JOBS.send({
    type: 'audit',
    sku: 'audit',
    buyer_email: body.buyer_email,
    upload_url: body.upload_url,
    stripe_session_id: body.stripe_session_id,
    branding: record.domain_verified
      ? {
          partner_slug: slug,
          display_name: record.display_name,
          logo_url: record.logo_url,
        }
      : undefined,
    rev_share: {
      partner_account: record.stripe_account_id,
      partner_share: REV_SHARE_PARTNER,
    },
  });

  return jsonResponse({ ok: true, queued: true });
}

async function createStripeConnectAccount(
  env: Env,
  email: string
): Promise<string> {
  if (!env.STRIPE_KEY || env.STRIPE_KEY.startsWith('sk_test_dummy')) {
    return `acct_dummy_${crypto.randomUUID()}`;
  }
  const resp = await fetch('https://api.stripe.com/v1/accounts', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${env.STRIPE_KEY}`,
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      type: 'express',
      email,
      'capabilities[transfers][requested]': 'true',
    }),
  });
  if (!resp.ok) throw new Error(`stripe account create failed: ${resp.status}`);
  const data = (await resp.json()) as { id: string };
  return data.id;
}

async function getStripeAccountLink(
  env: Env,
  accountId: string
): Promise<string> {
  if (accountId.startsWith('acct_dummy_')) {
    return 'https://example.com/dummy-onboarding';
  }
  const resp = await fetch('https://api.stripe.com/v1/account_links', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${env.STRIPE_KEY}`,
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      account: accountId,
      refresh_url: 'https://ntoledo319.github.io/Rupture/partners/onboarding',
      return_url: 'https://ntoledo319.github.io/Rupture/partners/onboarded',
      type: 'account_onboarding',
    }),
  });
  if (!resp.ok) throw new Error(`stripe account_link failed: ${resp.status}`);
  const data = (await resp.json()) as { url: string };
  return data.url;
}

export async function partnersRouter(
  request: Request,
  env: Env
): Promise<Response | null> {
  const url = new URL(request.url);
  const path = url.pathname;

  if (request.method === 'POST' && path === '/partners/signup') {
    return partnerSignup(request, env);
  }
  if (request.method === 'POST' && path.startsWith('/partners/verify/')) {
    return partnerVerifyDomain(request, env);
  }
  if (
    request.method === 'POST' &&
    /^\/partners\/[^/]+\/audit$/.test(path)
  ) {
    return partnerAudit(request, env);
  }
  return null;
}
