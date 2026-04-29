/**
 * LLM-on-rails support bot using Cloudflare Workers AI
 * Falls back to canned responses when AI quota exceeded
 */

import type { Env } from './index';

const SYSTEM_PROMPT = `You are the Rupture support bot. You help users with AWS deprecation migration questions.

You only answer questions about:
- Lambda runtime migrations (Node.js, Python)
- Amazon Linux 2 to AL2023 migrations
- Infrastructure as Code (SAM, CDK, Terraform, Serverless)
- Canary deployments and rollbacks
- Audit reports and findings

You must cite documentation URLs in your answers. Valid doc patterns:
- https://ntoledo319.github.io/Rupture/docs/...
- https://github.com/ntoledo319/Rupture/blob/main/...

If a question is outside your scope, politely decline and link to GitHub Discussions.

Keep answers concise and actionable. Never make up commands or URLs.`;

const FAQ_KNOWLEDGE = `
Common questions and answers:

Q: How do I scan my Lambda functions?
A: Run \`lambda-lifeline scan --region us-east-1\` to list all Node.js 20 Lambdas. Use \`--fixture\` for offline testing. Docs: https://github.com/ntoledo319/Rupture/tree/main/kits/lambda-lifeline

Q: Will codemods break my code?
A: No. All codemods are dry-run by default. Use \`--apply\` after reviewing changes. Each kit has 100+ tests. Docs: https://github.com/ntoledo319/Rupture#tests

Q: What is the refund policy?
A: Migration Pack purchases auto-refund if CI fails within 7 days. Audit PDFs are non-refundable but include verification. Terms: https://ntoledo319.github.io/Rupture/legal/terms

Q: How do I opt out of auto-PRs?
A: Add a \`.no-rupture\` file to your repository root. The bot will skip that repo.

Q: Can I use this for commercial projects?
A: Yes. The CLI is MIT licensed. Paid tiers add automation and reports.
`;

const CANNED_RESPONSES: Record<string, string> = {
  pricing: 'See https://ntoledo319.github.io/Rupture#pricing for current pricing. CLI is free (MIT). Paid tiers: Audit PDF ($299+), Migration Pack ($1,499), Org License ($14,999/yr), Drift Watch ($19/mo).',
  refund: 'Migration Pack: auto-refund if CI fails within 7 days. Audit PDF: includes verification URL, non-refundable. See Terms: https://ntoledo319.github.io/Rupture/legal/terms',
  install: 'Install any kit: `git clone https://github.com/ntoledo319/Rupture.git && cd kits/lambda-lifeline && pip install -e .`',
  license: 'CLI is MIT licensed. You can fork, modify, and use commercially. Paid tiers grant access to automation features, not code.',
  support: 'Free: GitHub Discussions at https://github.com/ntoledo319/Rupture/discussions. Paid tiers include automated support bot (this is it!).',
};

export async function supportHandler(request: Request, env: Env): Promise<Response> {
  if (request.method !== 'POST') {
    return new Response(JSON.stringify({ error: 'Method not allowed' }), {
      status: 405,
      headers: { 'Content-Type': 'application/json' },
    });
  }
  
  const body = await request.json() as { question: string };
  
  if (!body.question) {
    return new Response(JSON.stringify({ error: 'Missing question' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }
  
  const question = body.question.toLowerCase();
  
  // Quick canned response for common questions
  for (const [keyword, response] of Object.entries(CANNED_RESPONSES)) {
    if (question.includes(keyword)) {
      return new Response(JSON.stringify({
        answer: response,
        source: 'canned',
        confidence: 'high',
      }), {
        headers: { 'Content-Type': 'application/json' },
      });
    }
  }
  
  // Check AI daily cap
  const caps = await env.DAILY_CAPS.get('ai_usage:today');
  const aiUsage = caps ? JSON.parse(caps) : { neurons: 0 };
  
  if (aiUsage.neurons >= 10000) {
    // AI quota exhausted, use canned fallback
    return new Response(JSON.stringify({
      answer: 'See documentation at https://ntoledo319.github.io/Rupture or ask on GitHub Discussions: https://github.com/ntoledo319/Rupture/discussions',
      source: 'canned_fallback',
      reason: 'AI quota exceeded',
    }), {
      headers: { 'Content-Type': 'application/json' },
    });
  }
  
  // Try AI response
  try {
    const answer = await queryAI(body.question, env);
    
    // Validate answer has doc citations
    if (!answer.includes('https://')) {
      return new Response(JSON.stringify({
        answer: 'See documentation at https://ntoledo319.github.io/Rupture for more information.',
        source: 'canned_fallback',
        reason: 'AI response lacked citations',
      }), {
        headers: { 'Content-Type': 'application/json' },
      });
    }
    
    // Track AI usage (approximate)
    aiUsage.neurons += 100; // Rough estimate per query
    await env.DAILY_CAPS.put('ai_usage:today', JSON.stringify(aiUsage), {
      expirationTtl: getSecondsUntilMidnightUTC(),
    });
    
    return new Response(JSON.stringify({
      answer,
      source: 'ai',
      disclaimer: '[This is an automated response]',
    }), {
      headers: { 'Content-Type': 'application/json' },
    });
    
  } catch (error) {
    console.error('AI query failed:', error);
    
    return new Response(JSON.stringify({
      answer: 'See documentation at https://ntoledo319.github.io/Rupture or ask on GitHub Discussions.',
      source: 'error_fallback',
    }), {
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

async function queryAI(question: string, env: Env): Promise<string> {
  // Use Cloudflare Workers AI
  const messages = [
    { role: 'system', content: SYSTEM_PROMPT + '\n\n' + FAQ_KNOWLEDGE },
    { role: 'user', content: question },
  ];
  
  const response = await env.AI.run('@cf/meta/llama-3.1-8b-instruct', {
    messages,
    max_tokens: 500,
    temperature: 0.3,
  });
  
  return response.response || 'See documentation at https://ntoledo319.github.io/Rupture';
}

function getSecondsUntilMidnightUTC(): number {
  const now = new Date();
  const tomorrow = new Date(now);
  tomorrow.setUTCDate(tomorrow.getUTCDate() + 1);
  tomorrow.setUTCHours(0, 0, 0, 0);
  return Math.floor((tomorrow.getTime() - now.getTime()) / 1000);
}
