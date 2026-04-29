/**
 * Daily cost caps tracking for Rupture
 * Prevents exceeding free-tier limits
 */

import type { Env } from './index';

interface CapsResult {
  allowed: boolean;
  resetAt?: string;
  currentUsage?: Record<string, number>;
}

// Free tier limits (from pricing.yml)
const DAILY_LIMITS = {
  workers_requests: 100000,
  kv_reads: 100000,
  kv_writes: 1000,
  r2_reads: 1000000 / 30,     // Monthly / 30
  r2_writes: 10000000 / 30,
  ai_neurons: 10000,
  emails: 100,                 // Resend daily
};

export async function checkCaps(request: Request, env: Env): Promise<CapsResult> {
  const today = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
  const capKey = `caps:${today}`;
  
  // Get today's usage
  const usageData = await env.DAILY_CAPS.get(capKey);
  const usage = usageData ? JSON.parse(usageData) : {
    workers_requests: 0,
    kv_reads: 0,
    kv_writes: 0,
    r2_reads: 0,
    r2_writes: 0,
    ai_neurons: 0,
    emails: 0,
  };
  
  // Determine which counter to increment based on request
  const counter = getRequestCounter(request);
  
  // Check if we're near limit
  const current = usage[counter] || 0;
  const limit = DAILY_LIMITS[counter as keyof typeof DAILY_LIMITS] || Infinity;
  
  if (current >= limit) {
    // Calculate reset time (midnight UTC)
    const tomorrow = new Date();
    tomorrow.setUTCDate(tomorrow.getUTCDate() + 1);
    tomorrow.setUTCHours(0, 0, 0, 0);
    
    return {
      allowed: false,
      resetAt: tomorrow.toISOString(),
      currentUsage: usage,
    };
  }
  
  // Increment counter
  usage[counter] = current + 1;
  
  // Save (expires at end of day)
  const ttl = getSecondsUntilMidnightUTC();
  await env.DAILY_CAPS.put(capKey, JSON.stringify(usage), { expirationTtl: ttl });
  
  return {
    allowed: true,
    currentUsage: usage,
  };
}

function getRequestCounter(request: Request): string {
  const path = new URL(request.url).pathname;
  
  if (path.startsWith('/webhook/')) {
    return 'workers_requests';
  }
  
  if (path.includes('/support/')) {
    return 'ai_neurons';
  }
  
  if (path.startsWith('/upload')) {
    return request.method === 'GET' ? 'r2_reads' : 'r2_writes';
  }
  
  return 'workers_requests';
}

function getSecondsUntilMidnightUTC(): number {
  const now = new Date();
  const tomorrow = new Date(now);
  tomorrow.setUTCDate(tomorrow.getUTCDate() + 1);
  tomorrow.setUTCHours(0, 0, 0, 0);
  return Math.floor((tomorrow.getTime() - now.getTime()) / 1000);
}

export async function getCapStatus(env: Env): Promise<Record<string, { used: number; limit: number; percentage: number }>> {
  const today = new Date().toISOString().split('T')[0];
  const capKey = `caps:${today}`;
  
  const usageData = await env.DAILY_CAPS.get(capKey);
  const usage = usageData ? JSON.parse(usageData) : {};
  
  const status: Record<string, { used: number; limit: number; percentage: number }> = {};
  
  for (const [key, limit] of Object.entries(DAILY_LIMITS)) {
    const used = usage[key] || 0;
    status[key] = {
      used,
      limit,
      percentage: Math.round((used / limit) * 100),
    };
  }
  
  return status;
}
