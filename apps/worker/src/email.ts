/**
 * Resend email integration with DLQ fallback.
 *
 * Free tier: 3,000 emails/month, 100/day. On 4xx/5xx we re-queue with
 * exponential backoff (3 attempts) and finally land in the DLQ where the
 * DLQ-drainer opens a GitHub issue.
 */

import type { Env } from './index';

const RESEND_API = 'https://api.resend.com/emails';
const MAX_ATTEMPTS = 3;

export interface EmailJob {
  to: string;
  subject: string;
  html: string;
  from?: string;
  attachments?: Array<{ filename: string; content: string }>;
  attempt?: number;
  scope?: string;
}

export interface SendResult {
  ok: boolean;
  id?: string;
  status?: number;
  error?: string;
  retryable?: boolean;
}

export async function sendEmail(env: Env, job: EmailJob): Promise<SendResult> {
  if (!env.RESEND_API_KEY) {
    // No provider configured. Queue for later, surface to /status.
    await env.JOBS.send({
      type: 'email-pending-provider',
      job,
    });
    return { ok: false, error: 'no_provider', retryable: true };
  }

  const from = job.from || 'Rupture <noreply@ntoledo319.github.io>';
  const body = JSON.stringify({
    from,
    to: [job.to],
    subject: job.subject,
    html: job.html,
    attachments: job.attachments,
  });

  let response: Response;
  try {
    response = await fetch(RESEND_API, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${env.RESEND_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body,
    });
  } catch (e) {
    return {
      ok: false,
      error: `network: ${(e as Error).message}`,
      retryable: true,
    };
  }

  if (response.ok) {
    const data = (await response.json()) as { id: string };
    return { ok: true, id: data.id, status: response.status };
  }

  // Rate limited or transient — retry path.
  const retryable = response.status === 429 || response.status >= 500;
  return {
    ok: false,
    status: response.status,
    error: await response.text(),
    retryable,
  };
}

/**
 * Send with retry-and-DLQ. The handler retries within the worker; persistent
 * failures push to the queue with a delay; final failure lands in DLQ.
 */
export async function sendEmailWithRetry(
  env: Env,
  job: EmailJob
): Promise<SendResult> {
  const attempt = job.attempt ?? 1;
  const result = await sendEmail(env, job);

  if (result.ok) return result;

  if (result.retryable && attempt < MAX_ATTEMPTS) {
    const delaySeconds = Math.pow(2, attempt) * 30; // 60s, 120s, 240s
    await env.JOBS.send(
      { type: 'email-retry', job: { ...job, attempt: attempt + 1 } },
      { delaySeconds }
    );
    return result;
  }

  // Final failure — DLQ.
  await env.JOBS_DLQ.send({
    type: 'email-failed',
    job,
    lastError: result,
  });
  return result;
}

export function renderAuditDeliveryEmail(opts: {
  buyerEmail: string;
  pdfUrl: string;
  verifyUrl: string;
  rulePackVersion: string;
  inputSha: string;
}): string {
  return `<!doctype html>
<html><body style="font-family:system-ui,-apple-system,sans-serif;max-width:600px;margin:0 auto;padding:24px;line-height:1.6">
<h2 style="margin:0 0 12px">Your Rupture Audit is ready</h2>
<p>The audit you requested has been generated and signed.</p>
<p><a href="${opts.pdfUrl}" style="display:inline-block;background:#2563eb;color:#fff;padding:10px 18px;border-radius:6px;text-decoration:none">Download PDF</a></p>
<h3 style="margin-top:24px;font-size:14px;color:#374151">Verification</h3>
<ul style="font-size:13px;color:#4b5563">
<li>Input SHA-256: <code>${opts.inputSha}</code></li>
<li>Rule pack version: <code>${opts.rulePackVersion}</code></li>
<li>Verify authenticity: <a href="${opts.verifyUrl}">${opts.verifyUrl}</a></li>
</ul>
<p style="font-size:12px;color:#6b7280;margin-top:32px">This is a transactional message. You are receiving it because you purchased an Audit PDF on Rupture.</p>
</body></html>`;
}

export function renderRefundEmail(opts: {
  reason: string;
  amountCents: number;
}): string {
  return `<!doctype html>
<html><body style="font-family:system-ui,-apple-system,sans-serif;max-width:600px;margin:0 auto;padding:24px;line-height:1.6">
<h2 style="margin:0 0 12px">Refund issued</h2>
<p>Your purchase has been automatically refunded.</p>
<p><strong>Amount:</strong> $${(opts.amountCents / 100).toFixed(2)}<br>
<strong>Reason:</strong> ${opts.reason}</p>
<p>Funds will appear in your account within 5–10 business days, depending on your bank.</p>
</body></html>`;
}
