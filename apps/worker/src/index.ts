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

      if (path.startsWith('/api/audit')) {
        return await handleAudit(request, env, path);
      }

      if (path.startsWith('/api/pack')) {
        return await handlePack(request, env, path);
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
              error: error.message,
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

async function handleAudit(request: Request, env: Env, path: string): Promise<Response> {
  if (path === '/api/audit/checkout') {
    // Redirect to Stripe Payment Link for Audit
    const url = new URL(request.url);
    const email = url.searchParams.get('email') || 'anonymous';
    
    // TODO: Create checkout session with surge pricing logic
    return jsonResponse({ 
      checkoutUrl: '/api/audit/checkout-session',
      message: 'Checkout flow initiated'
    });
  }
  
  return jsonResponse({ error: 'Invalid audit endpoint' }, 404);
}

async function handlePack(request: Request, env: Env, path: string): Promise<Response> {
  if (path === '/api/pack/checkout') {
    return jsonResponse({
      checkoutUrl: '/api/pack/checkout-session',
      message: 'Migration Pack checkout initiated'
    });
  }
  
  return jsonResponse({ error: 'Invalid pack endpoint' }, 404);
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
  // Job processing logic
  console.log('Processing job:', job.type);
  
  switch (job.type) {
    case 'audit_pdf':
      // Trigger runner container
      break;
    case 'migration_pr':
      // Trigger PR creation
      break;
    case 'email':
      // Send email via Resend
      break;
    default:
      throw new Error(`Unknown job type: ${job.type}`);
  }
}
