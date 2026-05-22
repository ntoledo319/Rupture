/**
 * One-shot backfill: add metadata[project]=rupture to every existing Stripe
 * object owned by Rupture (Products, Prices, Payment Links). Reads IDs from
 * pricing.yml so it stays in sync with what's actually deployed.
 *
 * Idempotent: setting the same metadata twice is a no-op.
 *
 * Usage:
 *   STRIPE_KEY=rk_live_... npx tsx apps/worker/scripts/backfill_stripe_metadata.ts
 *
 * Works with restricted keys (rk_live_) that have write access to products,
 * prices, and payment_links.
 */

import { readFileSync } from 'fs';
import { join } from 'path';
// eslint-disable-next-line @typescript-eslint/no-var-requires
const yaml = require('js-yaml');

const STRIPE = 'https://api.stripe.com/v1';
const KEY = process.env.STRIPE_KEY;
if (!KEY) {
  console.error('STRIPE_KEY env var required');
  process.exit(2);
}

const PRICING_PATH = join(__dirname, '..', '..', '..', 'pricing.yml');

interface Tier {
  stripe_price_id?: string;
  stripe_payment_link?: string;
}
interface Sku {
  stripe_product?: string | null;
  stripe_price_id?: string;
  stripe_payment_link?: string;
  tiers?: Tier[];
}

async function tagObject(kind: 'products' | 'prices' | 'payment_links', id: string): Promise<void> {
  const body = new URLSearchParams({ 'metadata[project]': 'rupture' });
  const r = await fetch(`${STRIPE}/${kind}/${id}`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${KEY}`,
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: body.toString(),
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`${kind}/${id} -> ${r.status} ${text}`);
  }
  console.log(`  ok  ${kind}/${id}`);
}

function urlToPaymentLinkId(url?: string): string | undefined {
  if (!url) return undefined;
  // Payment Link URLs look like https://buy.stripe.com/<code>
  // We need the underlying plink_ ID. Skip — we'll search by URL via API instead.
  return undefined;
}

async function listPaymentLinkIds(): Promise<string[]> {
  // Iterate all active payment links and grab ids; the payment_link search API
  // does not support URL lookups but list does pagination.
  const ids: string[] = [];
  let url: string | null = `${STRIPE}/payment_links?limit=100`;
  while (url) {
    const r: Response = await fetch(url, {
      headers: { Authorization: `Bearer ${KEY}` },
    });
    if (!r.ok) {
      throw new Error(`payment_links list -> ${r.status} ${await r.text()}`);
    }
    const j = (await r.json()) as { data: Array<{ id: string; url: string; metadata: Record<string, string> }>; has_more: boolean };
    for (const pl of j.data) ids.push(pl.id);
    url = j.has_more ? `${STRIPE}/payment_links?limit=100&starting_after=${j.data[j.data.length - 1].id}` : null;
  }
  return ids;
}

async function main(): Promise<void> {
  const raw = readFileSync(PRICING_PATH, 'utf-8');
  const cfg = yaml.load(raw) as { skus: Record<string, Sku> };

  const products = new Set<string>();
  const prices = new Set<string>();
  const linkUrls = new Set<string>();

  for (const [, sku] of Object.entries(cfg.skus)) {
    if (sku.stripe_product) products.add(sku.stripe_product);
    if (sku.stripe_price_id) prices.add(sku.stripe_price_id);
    if (sku.stripe_payment_link) linkUrls.add(sku.stripe_payment_link);
    for (const tier of sku.tiers ?? []) {
      if (tier.stripe_price_id) prices.add(tier.stripe_price_id);
      if (tier.stripe_payment_link) linkUrls.add(tier.stripe_payment_link);
    }
  }

  console.log(`Products to tag: ${products.size}`);
  for (const id of products) await tagObject('products', id);

  console.log(`Prices to tag: ${prices.size}`);
  for (const id of prices) await tagObject('prices', id);

  // pricing.yml stores Payment Link URLs (buy.stripe.com/...), not the plink_ IDs.
  // We need IDs to update via API; list all payment links on the account, filter
  // to ones whose URL matches our pricing.yml entries.
  console.log(`Payment Link URLs to match: ${linkUrls.size}`);
  const allLinkIds = await listPaymentLinkIds();
  console.log(`Total payment_links on account: ${allLinkIds.length}`);

  let matched = 0;
  for (const linkId of allLinkIds) {
    const r = await fetch(`${STRIPE}/payment_links/${linkId}`, {
      headers: { Authorization: `Bearer ${KEY}` },
    });
    if (!r.ok) continue;
    const pl = (await r.json()) as { id: string; url: string };
    if (linkUrls.has(pl.url)) {
      await tagObject('payment_links', pl.id);
      matched++;
    }
  }
  console.log(`Payment Links tagged: ${matched} of ${linkUrls.size}`);

  if (matched < linkUrls.size) {
    console.warn(
      `WARNING: ${linkUrls.size - matched} payment links in pricing.yml had no matching plink_ on the account. ` +
        `They may be deleted, archived, or on a different account.`
    );
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
