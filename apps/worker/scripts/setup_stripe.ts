/**
 * Stripe products + prices + payment links bootstrap.
 *
 * Idempotent: re-runs do not duplicate. Reads pricing.yml as the source
 * of truth, writes the resulting Stripe IDs back into pricing.yml.
 *
 * Usage:
 *   STRIPE_KEY=sk_test_... npx tsx apps/worker/scripts/setup_stripe.ts
 */

import { readFileSync, writeFileSync } from 'fs';
import { join } from 'path';
// eslint-disable-next-line @typescript-eslint/no-var-requires
const yaml = require('js-yaml');

const STRIPE = 'https://api.stripe.com/v1';
const KEY = process.env.STRIPE_KEY;
if (!KEY) {
  console.error('STRIPE_KEY env var required (sk_test_... or sk_live_...)');
  process.exit(2);
}

const PRICING_PATH = join(__dirname, '..', '..', '..', 'pricing.yml');

interface Sku {
  name: string;
  description?: string;
  stripe_product?: string | null;
  stripe_price_id?: string;
  stripe_payment_link?: string;
  price_usd?: number;
  interval?: 'month' | 'year';
  tiers?: Array<{
    name: string;
    price_usd: number;
    description?: string;
    stripe_price_id?: string;
    stripe_payment_link?: string;
  }>;
}

async function stripeReq<T>(
  path: string,
  body?: Record<string, string>
): Promise<T> {
  const init: RequestInit = {
    method: body ? 'POST' : 'GET',
    headers: {
      Authorization: `Bearer ${KEY}`,
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  };
  if (body) init.body = new URLSearchParams(body).toString();
  const r = await fetch(`${STRIPE}${path}`, init);
  if (!r.ok) {
    throw new Error(`stripe ${path} failed: ${r.status} ${await r.text()}`);
  }
  return (await r.json()) as T;
}

async function findOrCreateProduct(
  name: string,
  description?: string
): Promise<{ id: string }> {
  const search = await stripeReq<{ data: Array<{ id: string }> }>(
    `/products/search?query=${encodeURIComponent(`name:'${name}' AND active:'true'`)}`
  );
  if (search.data.length > 0) return { id: search.data[0].id };
  return stripeReq<{ id: string }>('/products', {
    name,
    description: description ?? '',
    'metadata[managed_by]': 'rupture-setup',
  });
}

async function findOrCreatePrice(
  productId: string,
  amountUsd: number,
  interval?: 'month' | 'year',
  lookupKey?: string
): Promise<{ id: string }> {
  if (lookupKey) {
    const list = await stripeReq<{ data: Array<{ id: string }> }>(
      `/prices?lookup_keys[]=${encodeURIComponent(lookupKey)}&active=true&limit=1`
    );
    if (list.data.length > 0) return { id: list.data[0].id };
  }
  const body: Record<string, string> = {
    product: productId,
    unit_amount: String(Math.round(amountUsd * 100)),
    currency: 'usd',
  };
  if (interval) body['recurring[interval]'] = interval;
  if (lookupKey) body.lookup_key = lookupKey;
  return stripeReq<{ id: string }>('/prices', body);
}

async function createPaymentLink(priceId: string): Promise<{ url: string }> {
  const r = await stripeReq<{ url: string }>('/payment_links', {
    'line_items[0][price]': priceId,
    'line_items[0][quantity]': '1',
    'payment_method_types[0]': 'card',
    'metadata[managed_by]': 'rupture-setup',
  });
  return r;
}

async function provisionSku(key: string, sku: Sku): Promise<Sku> {
  if (!sku.stripe_product || sku.price_usd === 0) return sku;

  console.log(`[stripe] ${key}: ensure product`);
  const product = await findOrCreateProduct(sku.name, sku.description);
  sku.stripe_product = product.id;

  if (sku.tiers && sku.tiers.length) {
    for (const tier of sku.tiers) {
      const lookup = `rupture_${key}_${tier.name}`;
      const price = await findOrCreatePrice(
        product.id,
        tier.price_usd,
        undefined,
        lookup
      );
      tier.stripe_price_id = price.id;
      const link = await createPaymentLink(price.id);
      tier.stripe_payment_link = link.url;
      console.log(`  tier ${tier.name}: ${price.id}`);
    }
  } else if (sku.price_usd != null) {
    const lookup = `rupture_${key}`;
    const price = await findOrCreatePrice(
      product.id,
      sku.price_usd,
      sku.interval,
      lookup
    );
    sku.stripe_price_id = price.id;
    const link = await createPaymentLink(price.id);
    sku.stripe_payment_link = link.url;
    console.log(`  price: ${price.id}`);
  }

  return sku;
}

async function main(): Promise<void> {
  const raw = readFileSync(PRICING_PATH, 'utf-8');
  const cfg = yaml.load(raw) as { skus: Record<string, Sku> };

  for (const [key, sku] of Object.entries(cfg.skus)) {
    cfg.skus[key] = await provisionSku(key, sku);
  }

  writeFileSync(PRICING_PATH, yaml.dump(cfg, { lineWidth: 120 }), 'utf-8');
  console.log('pricing.yml updated.');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
