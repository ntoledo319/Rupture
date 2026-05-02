/**
 * Stripe integration for Rupture
 * - Checkout sessions
 * - Webhook handling with idempotency
 * - Refund processing
 */

import type { Env } from './index';
import { storeFiles } from './upload';
import {
  errorMessage,
  hmacSha256Hex,
  jsonResponse,
  readBody,
  stringField,
  timingSafeEqualHex,
  wantsHtmlRedirect,
} from './http';

interface StripeEvent {
  id: string;
  type: string;
  data: {
    object: any;
  };
}

export async function stripeRouter(request: Request, env: Env, path: string): Promise<Response> {
  if (path === '/webhook/stripe') {
    return handleStripeWebhook(request, env);
  }
  
  if (path === '/api/audit/checkout' || path === '/api/audit/checkout-session') {
    return createAuditCheckout(request, env);
  }
  
  if (path === '/api/pack/checkout' || path === '/api/pack/checkout-session') {
    return createPackCheckout(request, env);
  }
  
  return new Response('Not found', { status: 404 });
}

async function handleStripeWebhook(request: Request, env: Env): Promise<Response> {
  const payload = await request.text();
  const signature = request.headers.get('stripe-signature');
  
  if (!signature) {
    return new Response('Missing signature', { status: 400 });
  }
  
  // Verify webhook signature
  const isValid = await verifyWebhookSignature(payload, signature, env.STRIPE_WEBHOOK_SECRET);
  if (!isValid) {
    return new Response('Invalid signature', { status: 400 });
  }
  
  const event: StripeEvent = JSON.parse(payload);
  
  // Idempotency check
  const processed = await env.IDEMPOTENCY.get(`stripe:${event.id}`);
  if (processed) {
    return new Response('Already processed', { status: 200 });
  }
  
  // Mark as processed
  await env.IDEMPOTENCY.put(`stripe:${event.id}`, '1', { expirationTtl: 86400 * 30 });
  
  // Handle event types
  switch (event.type) {
    case 'checkout.session.completed':
      await handleCheckoutCompleted(event.data.object, env);
      break;
      
    case 'invoice.payment_succeeded':
      await handleSubscriptionPayment(event.data.object, env);
      break;
      
    case 'charge.refunded':
      await handleRefund(event.data.object, env);
      break;
      
    default:
      console.log(`Unhandled event type: ${event.type}`);
  }
  
  return new Response('OK', { status: 200 });
}

async function handleCheckoutCompleted(session: any, env: Env): Promise<void> {
  const metadata = session.metadata || {};
  const sku = metadata.sku;
  const email = session.customer_email || metadata.email;
  
  console.log(`Checkout completed: ${sku} for ${email}`);
  
  if (!env.JOBS) {
    console.error(`Queue NOT enabled. Cannot process ${sku} for ${email}`);
    // Store in KV for manual retry since Queue is disabled
    await env.IDEMPOTENCY.put(`failed_job:${session.id}`, JSON.stringify({
      type: sku,
      email,
      metadata,
      at: new Date().toISOString()
    }));
    return;
  }

  // Queue job based on SKU
  switch (sku) {
    case 'audit':
      await env.JOBS.send({
        type: 'audit_pdf',
        sessionId: session.id,
        email,
        uploadUrl: metadata.upload_url,
        deadline: metadata.deadline,
      });
      break;
      
    case 'migration_pack':
      await env.JOBS.send({
        type: 'migration_pr',
        sessionId: session.id,
        email,
        repo: metadata.repo,
        installationId: metadata.installation_id,
      });
      break;
      
    case 'org_license':
      await env.JOBS.send({
        type: 'license_key',
        sessionId: session.id,
        email,
        company: metadata.company,
      });
      break;
      
    case 'drift_watch':
      await env.JOBS.send({
        type: 'drift_watch_setup',
        sessionId: session.id,
        email,
        repo: metadata.repo,
        iamRole: metadata.iam_role,
      });
      break;
  }
}

async function handleSubscriptionPayment(invoice: any, env: Env): Promise<void> {
  // Handle recurring subscription payments
  console.log(`Subscription payment: ${invoice.id}`);
}

async function handleRefund(refund: any, env: Env): Promise<void> {
  // Log refund for audit trail
  console.log(`Refund processed: ${refund.id}`);
}

async function createAuditCheckout(request: Request, env: Env): Promise<Response> {
  if (request.method !== 'POST') {
    return jsonResponse({ error: 'Method not allowed' }, 405);
  }

  const body = await readBody(request);
  const email = stringField(body, 'email');
  const deadline = stringField(body, 'deadline');
  const uploadUrl = stringField(body, 'upload_url');

  if (!email) {
    return jsonResponse({ error: 'email required' }, 400);
  }
  
  // Calculate surge pricing based on deadline
  const daysUntil = deadline ? calculateDaysUntil(deadline) : 999;
  let price = 299;
  if (daysUntil <= 7) price = 599;
  else if (daysUntil <= 30) price = 399;
  
  // In test mode without a real key, return mock checkout URL
  if (env.STRIPE_KEY.startsWith('sk_test_dummy')) {
    const url = `https://checkout.stripe.com/test?price=${price}&email=${encodeURIComponent(email)}`;
    return checkoutResponse(request, url, price, 'test');
  }
  
  // Production or real test key: create real Stripe Checkout Session
  try {
    const session = await stripeRequest(env, '/v1/checkout/sessions', {
      'payment_method_types[0]': 'card',
      'line_items[0][price_data][currency]': 'usd',
      'line_items[0][price_data][product_data][name]': 'Rupture Audit PDF',
      'line_items[0][price_data][unit_amount]': String(price * 100),
      'line_items[0][quantity]': '1',
      'mode': 'payment',
      'success_url': 'https://ntoledo319.github.io/Rupture/verify?session_id={CHECKOUT_SESSION_ID}',
      'cancel_url': 'https://ntoledo319.github.io/Rupture/audit',
      'customer_email': email,
      'metadata[sku]': 'audit',
      'metadata[email]': email,
      'metadata[upload_url]': uploadUrl || '',
      'metadata[deadline]': deadline || '',
    });

    return checkoutResponse(
      request,
      session.url,
      price,
      env.STRIPE_KEY.startsWith('sk_test') ? 'test' : 'live'
    );
  } catch (error) {
    console.error('Stripe session creation failed:', error);
    return jsonResponse({ error: 'Failed to create checkout session' }, 500);
  }
}

async function createPackCheckout(request: Request, env: Env): Promise<Response> {
  if (request.method !== 'POST') {
    return jsonResponse({ error: 'Method not allowed' }, 405);
  }

  const body = await readBody(request);
  const email = stringField(body, 'email');
  const repo = stringField(body, 'repo');
  const installationId = stringField(body, 'installation_id');

  if (!email || !repo) {
    return jsonResponse({ error: 'email and repo required' }, 400);
  }
  
  // In test mode without a real key
  if (env.STRIPE_KEY.startsWith('sk_test_dummy')) {
    const url = `https://checkout.stripe.com/pack?price=1499&email=${encodeURIComponent(email)}&repo=${encodeURIComponent(repo)}`;
    return checkoutResponse(request, url, 1499, 'test');
  }

  try {
    const session = await stripeRequest(env, '/v1/checkout/sessions', {
      'payment_method_types[0]': 'card',
      'line_items[0][price_data][currency]': 'usd',
      'line_items[0][price_data][product_data][name]': 'Rupture Migration Pack',
      'line_items[0][price_data][unit_amount]': '149900',
      'line_items[0][quantity]': '1',
      'mode': 'payment',
      'success_url': 'https://ntoledo319.github.io/Rupture/status?session_id={CHECKOUT_SESSION_ID}',
      'cancel_url': 'https://ntoledo319.github.io/Rupture/pack',
      'customer_email': email,
      'metadata[sku]': 'migration_pack',
      'metadata[email]': email,
      'metadata[repo]': repo,
      'metadata[installation_id]': installationId || '',
    });

    return checkoutResponse(
      request,
      session.url,
      1499,
      env.STRIPE_KEY.startsWith('sk_test') ? 'test' : 'live'
    );
  } catch (error) {
    console.error('Stripe session creation failed:', error);
    return jsonResponse({ error: 'Failed to create checkout session' }, 500);
  }
}

function checkoutResponse(
  request: Request,
  url: string,
  price: number,
  mode: 'test' | 'live'
): Response {
  if (wantsHtmlRedirect(request)) {
    return Response.redirect(url, 303);
  }

  return jsonResponse({ url, price, mode });
}

async function stripeRequest(env: Env, path: string, body?: Record<string, string>): Promise<any> {
  const init: RequestInit = {
    method: body ? 'POST' : 'GET',
    headers: {
      'Authorization': `Bearer ${env.STRIPE_KEY}`,
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  };
  if (body) {
    init.body = new URLSearchParams(body).toString();
  }
  
  const response = await fetch(`https://api.stripe.com${path}`, init);
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Stripe API error (${response.status}): ${errorText}`);
  }
  return await response.json();
}

async function verifyWebhookSignature(
  payload: string,
  signature: string,
  secret: string
): Promise<boolean> {
  try {
    const timestamp = signature
      .split(',')
      .find((part) => part.startsWith('t='))
      ?.slice(2);
    if (!timestamp) return false;

    const timestampSeconds = Number(timestamp);
    if (!Number.isFinite(timestampSeconds)) return false;

    const ageSeconds = Math.abs(Date.now() / 1000 - timestampSeconds);
    if (ageSeconds > 300) return false;

    const expected = await hmacSha256Hex(secret, `${timestamp}.${payload}`);
    const signatures = signature
      .split(',')
      .filter((e) => e.startsWith('v1='))
      .map((e) => e.slice(3));

    return signatures.some((sig) => timingSafeEqualHex(expected, sig));
  } catch (error) {
    console.error('Signature verification failed:', error);
    return false;
  }
}

function calculateDaysUntil(deadline: string): number {
  const deadlineDate = new Date(deadline);
  const now = new Date();
  const diff = deadlineDate.getTime() - now.getTime();
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

export async function autoRefund(chargeId: string, reason: string, env: Env): Promise<void> {
  // Automated refund for failed CI
  console.log(`Auto-refunding charge ${chargeId}: ${reason}`);
  
  if (env.STRIPE_KEY.startsWith('sk_test_dummy')) {
    console.log('Skipping real refund in dummy mode');
    return;
  }

  try {
    await stripeRequest(env, '/v1/refunds', {
      charge: chargeId,
      reason: 'requested_by_customer',
      'metadata[reason]': reason,
      'metadata[managed_by]': 'rupture-auto-refund',
    });
    console.log(`Refund successful for ${chargeId}`);
  } catch (error) {
    console.error(`Refund failed for ${chargeId}:`, error);
    // Queue for retry or manual intervention if DLQ available
    if (env.JOBS_DLQ) {
      await env.JOBS_DLQ.send({
        type: 'refund_failed',
        chargeId,
        reason,
        error: errorMessage(error),
      });
    } else {
      await env.IDEMPOTENCY.put(`failed_refund:${chargeId}`, JSON.stringify({
        reason,
        error: errorMessage(error),
        at: new Date().toISOString()
      }));
    }
  }
}
