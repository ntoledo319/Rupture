/**
 * Idempotency middleware for webhook replay protection.
 *
 * Stripe and GitHub will retry webhooks. Without dedupe we double-charge,
 * double-fulfill, or double-refund. KV is the source of truth — first writer
 * wins, every subsequent caller gets a cached response.
 *
 * TTL is 30 days; events older than that won't be retried by Stripe.
 */

const IDEMPOTENCY_TTL_SECONDS = 30 * 24 * 60 * 60;

export interface IdempotencyResult<T = unknown> {
  fresh: boolean;
  cached?: T;
}

export async function checkIdempotency<T = unknown>(
  kv: KVNamespace,
  scope: string,
  eventId: string
): Promise<IdempotencyResult<T>> {
  const key = `idem:${scope}:${eventId}`;
  const cached = await kv.get(key, 'json');
  if (cached) {
    return { fresh: false, cached: cached as T };
  }
  return { fresh: true };
}

export async function recordIdempotency<T = unknown>(
  kv: KVNamespace,
  scope: string,
  eventId: string,
  result: T
): Promise<void> {
  const key = `idem:${scope}:${eventId}`;
  await kv.put(key, JSON.stringify(result), {
    expirationTtl: IDEMPOTENCY_TTL_SECONDS,
  });
}

/**
 * Wrap a webhook handler. First call executes, subsequent calls with the same
 * eventId return the cached response.
 */
export async function withIdempotency<T>(
  kv: KVNamespace,
  scope: string,
  eventId: string,
  handler: () => Promise<T>
): Promise<{ result: T; replayed: boolean }> {
  const check = await checkIdempotency<T>(kv, scope, eventId);
  if (!check.fresh) {
    return { result: check.cached as T, replayed: true };
  }
  const result = await handler();
  await recordIdempotency(kv, scope, eventId, result);
  return { result, replayed: false };
}
