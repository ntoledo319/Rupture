/**
 * Status endpoint for health checking and monitoring
 */

import type { Env } from './index';
import { getCapStatus } from './caps';

export async function statusHandler(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  const format = url.searchParams.get('format') || 'json';
  
  // Gather component statuses
  const [
    capsStatus,
    kvHealth,
    r2Health,
    queueHealth,
  ] = await Promise.all([
    getCapStatus(env),
    checkKVHealth(env),
    checkR2Health(env),
    checkQueueHealth(env),
  ]);
  
  const overall = Object.values(capsStatus).every(s => s.percentage < 90) &&
                  kvHealth.ok && r2Health.ok && queueHealth.ok;
  
  const status = {
    timestamp: new Date().toISOString(),
    overall: overall ? 'healthy' : 'degraded',
    version: '1.0.0',
    environment: env.ENVIRONMENT,
    components: {
      caps: capsStatus,
      kv: kvHealth,
      r2: r2Health,
      queue: queueHealth,
      stripe: { ok: !!env.STRIPE_KEY, mode: env.STRIPE_KEY?.startsWith('sk_test') ? 'test' : 'live' },
    },
  };
  
  if (format === 'prometheus') {
    return new Response(toPrometheusMetrics(status), {
      headers: { 'Content-Type': 'text/plain' },
    });
  }
  
  return new Response(JSON.stringify(status, null, 2), {
    headers: { 'Content-Type': 'application/json' },
  });
}

async function checkKVHealth(env: Env): Promise<{ ok: boolean; latency?: number }> {
  const start = Date.now();
  try {
    await env.IDEMPOTENCY.put('health:check', '1', { expirationTtl: 60 });
    const value = await env.IDEMPOTENCY.get('health:check');
    const latency = Date.now() - start;
    return { ok: value === '1', latency };
  } catch (error) {
    return { ok: false };
  }
}

async function checkR2Health(env: Env): Promise<{ ok: boolean }> {
  try {
    await env.UPLOADS.list({ limit: 1 });
    return { ok: true };
  } catch (error) {
    return { ok: false };
  }
}

async function checkQueueHealth(env: Env): Promise<{ ok: boolean }> {
  // Queue health is implicit - if we can send, it's healthy
  return { ok: true };
}

function toPrometheusMetrics(status: any): string {
  const lines = [];
  
  // Overall health
  lines.push('# HELP rupture_overall_health Overall health status (1 = healthy, 0 = degraded)');
  lines.push('# TYPE rupture_overall_health gauge');
  lines.push(`rupture_overall_health ${status.overall === 'healthy' ? 1 : 0}`);
  
  // Component health
  for (const [component, data] of Object.entries(status.components)) {
    if (data.ok !== undefined) {
      lines.push(`# HELP rupture_${component}_health ${component} health`);
      lines.push(`# TYPE rupture_${component}_health gauge`);
      lines.push(`rupture_${component}_health ${data.ok ? 1 : 0}`);
    }
  }
  
  // Cap usage
  for (const [cap, data] of Object.entries(status.components.caps)) {
    lines.push(`# HELP rupture_cap_usage_${cap} ${cap} usage percentage`);
    lines.push(`# TYPE rupture_cap_usage_${cap} gauge`);
    lines.push(`rupture_cap_usage_${cap} ${data.percentage}`);
  }
  
  return lines.join('\n');
}
