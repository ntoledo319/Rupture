/**
 * Rupture Cloudflare Worker
 * Main router for all API endpoints and webhooks
 */

import { stripeRouter } from './stripe';
import { githubRouter } from './github';
import { uploadHandler } from './upload';
import { licenseRouter } from './license';
import { statusHandler } from './status';
import { supportHandler } from './support';
import { rateLimitMiddleware } from './ratelimit';
import { checkCaps } from './caps';
import { partnersRouter } from './partners';
import { errorMessage } from './http';
import { generateLicenseKey } from './license';
import { sendEmailWithRetry } from './email';

export interface Env {
  IDEMPOTENCY: KVNamespace;
  RATE_LIMITS: KVNamespace;
  DAILY_CAPS: KVNamespace;
  UPLOADS?: R2Bucket;
  JOBS?: Queue;
  JOBS_DLQ?: Queue;
  AI: any;
  STRIPE_KEY: string;
  STRIPE_WEBHOOK_SECRET: string;
  RESEND_API_KEY?: string;
  GITHUB_APP_ID: string;
  GITHUB_APP_PRIVATE_KEY: string;
  GITHUB_WEBHOOK_SECRET?: string;
  ENVIRONMENT: string;
}

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
};

export default {
  async fetch(
    request: Request,
    env: Env,
    ctx: ExecutionContext
  ): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;

    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: CORS_HEADERS });
    }

    try {
      // Rate limiting (token bucket)
      const rateLimitResult = await rateLimitMiddleware(request, env);
      if (!rateLimitResult.allowed) {
        return jsonResponse(
          { error: 'Rate limit exceeded', retryAfter: rateLimitResult.retryAfter },
          429
        );
      }

      // Daily caps check
      const capsResult = await checkCaps(request, env);
      if (!capsResult.allowed) {
        return jsonResponse(
          { error: 'Daily capacity exceeded', resetAt: capsResult.resetAt },
          503
        );
      }

      // Router
      if (path === '/health') {
        return jsonResponse({ ok: true, env: env.ENVIRONMENT });
      }

      if (path === '/status' || path === '/status.json') {
        return await statusHandler(request, env);
      }

      if (path === '/support/ask') {
        return await supportHandler(request, env);
      }

      if (
        path.startsWith('/api/audit') ||
        path.startsWith('/api/pack') ||
        path === '/pack/install'
      ) {
        return await stripeOrPackRouter(request, env, path);
      }

      if (path.startsWith('/api/license')) {
        return await licenseRouter(request, env, path);
      }

      if (path.startsWith('/webhook/stripe')) {
        return await stripeRouter(request, env, path);
      }

      if (path.startsWith('/webhook/github')) {
        return await githubRouter(request, env, path);
      }

      if (path.startsWith('/upload')) {
        return await uploadHandler(request, env, path);
      }

      if (path.startsWith('/verify/')) {
        return await verifyHandler(request, env, path);
      }

      if (path === '/abuse') {
        return await abuseHandler(request, env);
      }

      if (path.startsWith('/partners')) {
        const r = await partnersRouter(request, env);
        if (r) return r;
      }

      return jsonResponse({ error: 'Not found' }, 404);

    } catch (error) {
      console.error('Worker error:', error);
      return jsonResponse({ 
        error: 'Internal server error',
        requestId: crypto.randomUUID()
      }, 500);
    }
  },

  async queue(batch: MessageBatch<any>, env: Env, ctx: ExecutionContext) {
    // Process queued jobs
    for (const message of batch.messages) {
      try {
        await processJob(message.body, env);
        message.ack();
      } catch (error) {
        console.error('Job failed:', error);
        if (message.attempts >= 3) {
          // Move to DLQ if available
          if (env.JOBS_DLQ) {
            await env.JOBS_DLQ.send({
              ...message.body,
              error: errorMessage(error),
              failedAt: new Date().toISOString(),
            });
          } else {
            console.error('No DLQ configured, message dropped after 3 attempts');
          }
          message.ack();
        } else {
          message.retry();
        }
      }
    }
  },
};

// Helper functions
function jsonResponse(data: any, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...CORS_HEADERS,
    },
  });
}

async function stripeOrPackRouter(request: Request, env: Env, path: string): Promise<Response> {
  if (
    path === '/api/audit/checkout' ||
    path === '/api/audit/checkout-session' ||
    path === '/api/pack/checkout' ||
    path === '/api/pack/checkout-session'
  ) {
    return await stripeRouter(request, env, path);
  }

  if (path === '/pack/install') {
    return await githubRouter(request, env, path);
  }

  return jsonResponse({ error: 'Invalid commerce endpoint' }, 404);
}

async function verifyHandler(request: Request, env: Env, path: string): Promise<Response> {
  const sha = path.replace('/verify/', '');
  
  // Look up verification in KV
  const verification = await env.IDEMPOTENCY.get(`verify:${sha}`);
  
  if (!verification) {
    return jsonResponse({ valid: false, error: 'Hash not found' }, 404);
  }
  
  const data = JSON.parse(verification);
  return jsonResponse({
    valid: true,
    generatedAt: data.generatedAt,
    rulePackVersion: data.rulePackVersion,
    sha256: sha,
  });
}

async function abuseHandler(request: Request, env: Env): Promise<Response> {
  if (request.method !== 'POST') {
    return jsonResponse({ error: 'Method not allowed' }, 405);
  }

  const body = await request.json() as { repo?: string };
  
  if (!body.repo) {
    return jsonResponse({ error: 'Missing repo field' }, 400);
  }

  // Add to abuse blocklist
  await env.IDEMPOTENCY.put(
    `abuse:${body.repo}`,
    JSON.stringify({
      blockedAt: new Date().toISOString(),
      reason: 'abuse_report',
    }),
    { expirationTtl: 86400 * 30 } // 30 days
  );

  return jsonResponse({ 
    blocked: true,
    repo: body.repo,
    message: 'Repository blocked from auto-PRs'
  });
}

async function processJob(job: any, env: Env): Promise<void> {
  console.log('Processing job:', job.type);
  
  switch (job.type) {
    case 'email':
      await sendEmailWithRetry(env, job);
      break;
    case 'email-retry':
      await sendEmailWithRetry(env, job.job);
      break;
    case 'license_key': {
      const key = await generateLicenseKey(
        job.company || 'Rupture customer',
        job.email,
        env
      );
      await sendEmailWithRetry(env, {
        to: job.email,
        subject: 'Your Rupture org license key',
        html: `<p>Your Rupture license key:</p><p><code>${key}</code></p>`,
        scope: 'license_key',
      });
      break;
    }
    case 'license_inquiry':
      await storeOperationalJob(env, job, 'license_inquiry_received');
      break;
    case 'audit_pdf':
      await storeOperationalJob(env, job, 'requires_audit_runner');
      break;
    case 'migration_pr':
      await storeOperationalJob(env, job, 'requires_migration_runner');
      break;
    case 'drift_watch_setup':
      await storeOperationalJob(env, job, 'requires_drift_watch_runner');
      break;
    case 'initial_scan':
      await storeOperationalJob(env, job, 'initial_scan_queued');
      break;
    case 'check_refund_eligibility':
      await storeOperationalJob(env, job, 'refund_eligibility_check_due');
      break;
    case 'email-pending-provider':
    case 'email-failed':
    case 'refund_failed':
      await storeOperationalJob(env, job, job.type);
      break;
    default:
      throw new Error(`Unknown job type: ${job.type}`);
  }
}

async function storeOperationalJob(
  env: Env,
  job: Record<string, unknown>,
  status: string
): Promise<void> {
  await env.IDEMPOTENCY.put(
    `ops_job:${status}:${crypto.randomUUID()}`,
    JSON.stringify({
      ...job,
      status,
      storedAt: new Date().toISOString(),
    }),
    { expirationTtl: 86400 * 30 }
  );
}
