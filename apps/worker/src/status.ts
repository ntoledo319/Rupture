/**
 * Status endpoint for health checking and monitoring
 */

import type { Env } from './index';
import { getCapStatus } from './caps';

type ComponentHealth = { ok: boolean; latency?: number; configured?: boolean };
type CapStatus = Record<string, { used: number; limit: number; percentage: number }>;

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
      email: { ok: !!env.RESEND_API_KEY, configured: !!env.RESEND_API_KEY },
      github: { ok: !!env.GITHUB_APP_ID, configured: !!env.GITHUB_APP_ID },
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

async function checkKVHealth(env: Env): Promise<ComponentHealth> {
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

async function checkR2Health(env: Env): Promise<ComponentHealth> {
  if (!env.UPLOADS) {
    return { ok: false, configured: false };
  }

  try {
    await env.UPLOADS.list({ limit: 1 });
    return { ok: true, configured: true };
  } catch (error) {
    return { ok: false, configured: true };
  }
}

async function checkQueueHealth(env: Env): Promise<ComponentHealth> {
  return { ok: !!env.JOBS, configured: !!env.JOBS };
}

function toPrometheusMetrics(status: {
  overall: string;
  components: {
    caps: CapStatus;
    kv: ComponentHealth;
    r2: ComponentHealth;
    queue: ComponentHealth;
    stripe: { ok: boolean; mode: string };
    email: ComponentHealth;
    github: ComponentHealth;
  };
}): string {
  const lines = [];
  
  // Overall health
  lines.push('# HELP rupture_overall_health Overall health status (1 = healthy, 0 = degraded)');
  lines.push('# TYPE rupture_overall_health gauge');
  lines.push(`rupture_overall_health ${status.overall === 'healthy' ? 1 : 0}`);
  
  // Component health
  for (const [component, data] of Object.entries(status.components)) {
    if (isComponentHealth(data)) {
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

function isComponentHealth(value: unknown): value is ComponentHealth {
  return typeof value === 'object' && value !== null && 'ok' in value;
}
