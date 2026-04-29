import { describe, expect, it } from 'vitest';
import {
  checkIdempotency,
  recordIdempotency,
  withIdempotency,
} from '../src/idempotency';

class MemKV {
  private m = new Map<string, string>();
  async get(k: string, _t?: 'json') {
    const v = this.m.get(k);
    if (!v) return null;
    return _t === 'json' ? JSON.parse(v) : v;
  }
  async put(k: string, v: string) {
    this.m.set(k, v);
  }
}

describe('idempotency', () => {
  it('first call is fresh, second is replay', async () => {
    const kv = new MemKV() as unknown as KVNamespace;
    const r1 = await checkIdempotency(kv, 'stripe', 'evt_123');
    expect(r1.fresh).toBe(true);
    await recordIdempotency(kv, 'stripe', 'evt_123', { ok: true });
    const r2 = await checkIdempotency(kv, 'stripe', 'evt_123');
    expect(r2.fresh).toBe(false);
    expect(r2.cached).toEqual({ ok: true });
  });

  it('withIdempotency only runs handler once', async () => {
    const kv = new MemKV() as unknown as KVNamespace;
    let calls = 0;
    const h = async () => {
      calls += 1;
      return { processed: calls };
    };
    const a = await withIdempotency(kv, 'gh', 'evt_x', h);
    const b = await withIdempotency(kv, 'gh', 'evt_x', h);
    expect(calls).toBe(1);
    expect(a.replayed).toBe(false);
    expect(b.replayed).toBe(true);
    expect(b.result).toEqual(a.result);
  });
});
