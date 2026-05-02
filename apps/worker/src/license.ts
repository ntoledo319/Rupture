/**
 * License key management for Org License tier
 */

import type { Env } from './index';
import { jsonResponse, readBody, stringField } from './http';

export async function licenseRouter(request: Request, env: Env, path: string): Promise<Response> {
  if (path === '/api/license/inquiry') {
    return handleLicenseInquiry(request, env);
  }
  
  if (path === '/api/license/verify') {
    return verifyLicense(request, env);
  }
  
  if (path === '/api/license/validate') {
    return validateLicenseKey(request, env);
  }
  
  return new Response('Not found', { status: 404 });
}

async function handleLicenseInquiry(request: Request, env: Env): Promise<Response> {
  const body = await readBody(request);
  const email = stringField(body, 'email');
  const company = stringField(body, 'company');
  const reposRaw = stringField(body, 'repos');

  if (!email || !company) {
    return jsonResponse({ error: 'email and company required' }, 400);
  }
  
  // Queue inquiry for processing
  const job = {
    type: 'license_inquiry',
    email,
    company,
    repos: reposRaw ? Number(reposRaw) : undefined,
    submittedAt: new Date().toISOString(),
  };
  if (env.JOBS) {
    await env.JOBS.send(job);
  } else {
    await env.IDEMPOTENCY.put(
      `license_inquiry:${crypto.randomUUID()}`,
      JSON.stringify(job),
      { expirationTtl: 86400 * 30 }
    );
  }
  
  return jsonResponse({
    received: true,
    message: 'License inquiry received. Check your email within 24 hours.',
  });
}

async function verifyLicense(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  const key = url.searchParams.get('key');
  
  if (!key) {
    return new Response(JSON.stringify({ valid: false, error: 'Missing license key' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }
  
  // Look up license
  const licenseData = await env.IDEMPOTENCY.get(`license:${key}`);
  
  if (!licenseData) {
    return new Response(JSON.stringify({ valid: false, error: 'Invalid license key' }), {
      status: 404,
      headers: { 'Content-Type': 'application/json' },
    });
  }
  
  const license = JSON.parse(licenseData);
  const now = new Date();
  const expiresAt = new Date(license.expiresAt);
  
  if (now > expiresAt) {
    return new Response(JSON.stringify({
      valid: false,
      error: 'License expired',
      expiredAt: license.expiresAt,
    }), {
      status: 403,
      headers: { 'Content-Type': 'application/json' },
    });
  }
  
  return new Response(JSON.stringify({
    valid: true,
    company: license.company,
    expiresAt: license.expiresAt,
    features: ['rule_feed', 'private_rules', 'unlimited_runs'],
  }), {
    headers: { 'Content-Type': 'application/json' },
  });
}

async function validateLicenseKey(request: Request, env: Env): Promise<Response> {
  const body = await readBody(request);
  const key = stringField(body, 'key');
  const action = stringField(body, 'action') || 'validate';

  if (!key) {
    return jsonResponse({ valid: false, error: 'Missing license key' }, 400);
  }
  
  const result = await verifyLicense(
    new Request(`${request.url}?key=${encodeURIComponent(key)}`),
    env
  );
  
  const data = (await result.json()) as { valid?: boolean };
  
  if (!data.valid) {
    return new Response(JSON.stringify(data), {
      status: result.status,
      headers: { 'Content-Type': 'application/json' },
    });
  }
  
  // Log usage
  await env.IDEMPOTENCY.put(
    `license:usage:${key}:${Date.now()}`,
    JSON.stringify({
      action,
      timestamp: new Date().toISOString(),
    }),
    { expirationTtl: 86400 * 365 } // Keep usage logs for 1 year
  );
  
  return new Response(JSON.stringify({
    valid: true,
    action,
    timestamp: new Date().toISOString(),
  }), {
    headers: { 'Content-Type': 'application/json' },
  });
}

export async function generateLicenseKey(
  company: string,
  email: string,
  env: Env
): Promise<string> {
  // Generate a license key
  const keyParts = [];
  for (let i = 0; i < 4; i++) {
    keyParts.push(Array.from(crypto.getRandomValues(new Uint8Array(4)))
      .map(b => b.toString(16).padStart(2, '0').toUpperCase())
      .join(''));
  }
  const key = keyParts.join('-');
  
  // Calculate expiration (1 year from now)
  const expiresAt = new Date();
  expiresAt.setFullYear(expiresAt.getFullYear() + 1);
  
  // Store license
  await env.IDEMPOTENCY.put(
    `license:${key}`,
    JSON.stringify({
      company,
      email,
      createdAt: new Date().toISOString(),
      expiresAt: expiresAt.toISOString(),
      key,
    }),
    { expirationTtl: 86400 * 366 } // 1 year + 1 day
  );
  
  return key;
}
