import { describe, expect, it } from 'vitest';
import worker, { type Env } from '../src/index';

class MemKV {
  private m = new Map<string, string>();

  async get(k: string, t?: 'json') {
    const v = this.m.get(k);
    if (!v) return null;
    return t === 'json' ? JSON.parse(v) : v;
  }

  async put(k: string, v: string) {
    this.m.set(k, v);
  }

  async delete(k: string) {
    this.m.delete(k);
  }
}

function env(): Env {
  const kv = new MemKV() as unknown as KVNamespace;
  return {
    IDEMPOTENCY: kv,
    RATE_LIMITS: kv,
    DAILY_CAPS: kv,
    AI: { run: async () => ({ response: 'https://ntoledo319.github.io/Rupture' }) },
    STRIPE_KEY: 'sk_test_dummy',
    STRIPE_WEBHOOK_SECRET: 'whsec_test',
    GITHUB_APP_ID: '123',
    GITHUB_APP_PRIVATE_KEY: 'private',
    ENVIRONMENT: 'test',
  };
}

const ctx = {
  waitUntil() {},
  passThroughOnException() {},
} as unknown as ExecutionContext;

describe('worker routes', () => {
  it('posts static audit checkout form to Stripe redirect', async () => {
    const request = new Request('https://worker.test/api/audit/checkout', {
      method: 'POST',
      headers: {
        Accept: 'text/html',
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: 'email=buyer%40example.com',
    });

    const response = await worker.fetch(request, env(), ctx);

    expect(response.status).toBe(303);
    expect(response.headers.get('Location')).toContain(
      'https://checkout.stripe.com/test?price=299&email=buyer%40example.com'
    );
  });
});
