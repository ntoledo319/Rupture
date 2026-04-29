/**
 * Token bucket rate limiting for Rupture Worker
 * Tracks per-IP and per-email limits in Cloudflare KV
 */

import type { Env } from './index';

interface RateLimitResult {
  allowed: boolean;
  retryAfter?: number;
  remaining?: number;
  limit?: number;
}

const BUCKET_SIZE = 100;      // requests per window
const REFILL_RATE = 10;       // requests per second
const WINDOW_SECONDS = 60;    // 1 minute window

export async function rateLimitMiddleware(
  request: Request,
  env: Env
): Promise<RateLimitResult> {
  const clientId = getClientId(request);
  const key = `ratelimit:${clientId}`;
  const now = Date.now();
  
  // Get current bucket state
  const bucketData = await env.RATE_LIMITS.get(key);
  let bucket = bucketData ? JSON.parse(bucketData) : {
    tokens: BUCKET_SIZE,
    lastRefill: now,
  };
  
  // Calculate token refill
  const elapsedMs = now - bucket.lastRefill;
  const tokensToAdd = Math.floor((elapsedMs / 1000) * REFILL_RATE);
  bucket.tokens = Math.min(BUCKET_SIZE, bucket.tokens + tokensToAdd);
  bucket.lastRefill = now;
  
  // Check if request can be processed
  if (bucket.tokens < 1) {
    // Calculate retry after
    const tokensNeeded = 1 - bucket.tokens;
    const msUntilRefill = (tokensNeeded / REFILL_RATE) * 1000;
    
    // Save bucket state
    await env.RATE_LIMITS.put(key, JSON.stringify(bucket), {
      expirationTtl: WINDOW_SECONDS,
    });
    
    return {
      allowed: false,
      retryAfter: Math.ceil(msUntilRefill / 1000),
      remaining: 0,
      limit: BUCKET_SIZE,
    };
  }
  
  // Consume token
  bucket.tokens -= 1;
  
  // Save bucket state
  await env.RATE_LIMITS.put(key, JSON.stringify(bucket), {
    expirationTtl: WINDOW_SECONDS,
  });
  
  return {
    allowed: true,
    remaining: Math.floor(bucket.tokens),
    limit: BUCKET_SIZE,
  };
}

function getClientId(request: Request): string {
  // Use CF-Connecting-IP if available (Cloudflare sets this)
  const cfIp = request.headers.get('CF-Connecting-IP');
  if (cfIp) return cfIp;
  
  // Fall back to X-Forwarded-For
  const forwarded = request.headers.get('X-Forwarded-For');
  if (forwarded) {
    return forwarded.split(',')[0].trim();
  }
  
  // Last resort: use a hash of User-Agent + Accept-Language
  const ua = request.headers.get('User-Agent') || 'unknown';
  const lang = request.headers.get('Accept-Language') || 'en';
  return hashString(`${ua}:${lang}`);
}

function hashString(str: string): string {
  // Simple hash for fallback client ID
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return `anon_${Math.abs(hash).toString(16)}`;
}
