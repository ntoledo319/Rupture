/**
 * Stripe integration for Rupture
 * - Checkout sessions
 * - Webhook handling with idempotency
 * - Refund processing
 */

import type { Env } from './index';

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
  
  if (path === '/api/audit/checkout-session') {
    return createAuditCheckout(request, env);
  }
  
  if (path === '/api/pack/checkout-session') {
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
  const body = await request.json() as { email: string; deadline?: string };
  
  // Calculate surge pricing based on deadline
  const daysUntil = body.deadline ? calculateDaysUntil(body.deadline) : 999;
  let price = 299;
  if (daysUntil <= 7) price = 599;
  else if (daysUntil <= 30) price = 399;
  
  // In test mode, return mock checkout URL
  if (env.ENVIRONMENT !== 'production' || env.STRIPE_KEY.startsWith('sk_test')) {
    return new Response(JSON.stringify({
      url: `https://checkout.stripe.com/test?price=${price}&email=${encodeURIComponent(body.email)}`,
      price,
      mode: 'test',
    }), {
      headers: { 'Content-Type': 'application/json' },
    });
  }
  
  // Production: create real Stripe Checkout Session
  // This would call Stripe API
  return new Response(JSON.stringify({
    url: 'https://checkout.stripe.com/...',
    price,
    mode: 'live',
  }), {
    headers: { 'Content-Type': 'application/json' },
  });
}

async function createPackCheckout(request: Request, env: Env): Promise<Response> {
  const body = await request.json() as { email: string; repo: string };
  
  return new Response(JSON.stringify({
    url: `https://checkout.stripe.com/pack?price=1499&email=${encodeURIComponent(body.email)}&repo=${encodeURIComponent(body.repo)}`,
    price: 1499,
    guarantee: '7-day auto-refund if CI fails',
  }), {
    headers: { 'Content-Type': 'application/json' },
  });
}

async function verifyWebhookSignature(
  payload: string,
  signature: string,
  secret: string
): Promise<boolean> {
  // Implement Stripe webhook signature verification
  // Using Web Crypto API
  try {
    const encoder = new TextEncoder();
    const key = await crypto.subtle.importKey(
      'raw',
      encoder.encode(secret),
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['sign']
    );
    
    const sig = await crypto.subtle.sign('HMAC', key, encoder.encode(payload));
    const sigHex = Array.from(new Uint8Array(sig))
      .map(b => b.toString(16).padStart(2, '0'))
      .join('');
    
    // Parse Stripe signature header
    const elements = signature.split(',');
    const signatures = elements
      .filter(e => e.startsWith('v1='))
      .map(e => e.slice(3));
    
    return signatures.includes(sigHex);
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
  
  // In production, this would call Stripe API
  // await stripe.refunds.create({ charge: chargeId, reason: 'requested_by_customer' });
}
