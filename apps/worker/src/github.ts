/**
 * GitHub App integration for Rupture
 * - Webhook handling
 * - PR creation
 * - Installation management
 */

import type { Env } from './index';

export async function githubRouter(request: Request, env: Env, path: string): Promise<Response> {
  if (path === '/webhook/github') {
    return handleGitHubWebhook(request, env);
  }
  
  if (path === '/pack/install') {
    return generateInstallUrl(env);
  }
  
  return new Response('Not found', { status: 404 });
}

async function handleGitHubWebhook(request: Request, env: Env): Promise<Response> {
  const payload = await request.json();
  const eventType = request.headers.get('X-GitHub-Event');
  
  console.log(`GitHub webhook: ${eventType}`);
  
  switch (eventType) {
    case 'installation':
      await handleInstallation(payload, env);
      break;
      
    case 'installation_repositories':
      await handleInstallationRepos(payload, env);
      break;
      
    case 'check_run':
      await handleCheckRun(payload, env);
      break;
      
    case 'push':
      await handlePush(payload, env);
      break;
  }
  
  return new Response('OK', { status: 200 });
}

async function handleInstallation(payload: any, env: Env): Promise<void> {
  const action = payload.action; // created, deleted, suspended
  const installation = payload.installation;
  
  if (action === 'created') {
    // Store installation info
    await env.IDEMPOTENCY.put(
      `github:install:${installation.id}`,
      JSON.stringify({
        id: installation.id,
        account: installation.account.login,
        repositories: payload.repositories || [],
        createdAt: new Date().toISOString(),
      })
    );
    
    // Schedule initial scan (with jitter to avoid thundering herd)
    for (const repo of payload.repositories || []) {
      const jitter = Math.floor(Math.random() * 60000); // 0-60 seconds
      await env.JOBS.send({
        type: 'initial_scan',
        installationId: installation.id,
        repo: repo.full_name,
      }, { delaySeconds: Math.floor(jitter / 1000) });
    }
  }
  
  if (action === 'deleted') {
    // Clean up installation data
    await env.IDEMPOTENCY.delete(`github:install:${installation.id}`);
  }
}

async function handleInstallationRepos(payload: any, env: Env): Promise<void> {
  // Handle repositories added/removed from existing installation
  const installation = payload.installation;
  const action = payload.action;
  
  if (action === 'added') {
    for (const repo of payload.repositories_added || []) {
      await env.JOBS.send({
        type: 'initial_scan',
        installationId: installation.id,
        repo: repo.full_name,
      });
    }
  }
}

async function handleCheckRun(payload: any, env: Env): Promise<void> {
  // Check if this is a migration PR check run
  const checkRun = payload.check_run;
  const pr = checkRun.pull_requests?.[0];
  
  if (!pr) return;
  
  // Check if PR is from Rupture
  const branchName = pr.head?.ref || '';
  if (!branchName.startsWith('rupture/migrate-')) return;
  
  const conclusion = checkRun.conclusion;
  const repo = payload.repository?.full_name;
  const prNumber = pr.number;
  
  if (conclusion === 'failure') {
    // Queue refund check (7-day window)
    await env.IDEMPOTENCY.put(
      `pr:ci-failed:${repo}:${prNumber}`,
      JSON.stringify({
        failedAt: new Date().toISOString(),
        checkRunId: checkRun.id,
        conclusion: conclusion,
      }),
      { expirationTtl: 86400 * 8 } // 8 days to be safe
    );
    
    // Schedule refund check in 7 days
    await env.JOBS.send({
      type: 'check_refund_eligibility',
      repo,
      prNumber,
      failedAt: new Date().toISOString(),
    }, { delaySeconds: 86400 * 7 });
  }
  
  if (conclusion === 'success') {
    // Remove any pending refund
    await env.IDEMPOTENCY.delete(`pr:ci-failed:${repo}:${prNumber}`);
  }
}

async function handlePush(payload: any, env: Env): Promise<void> {
  // Check for .no-rupture file
  const commits = payload.commits || [];
  const repo = payload.repository?.full_name;
  
  for (const commit of commits) {
    if (commit.added?.includes('.no-rupture') || commit.modified?.includes('.no-rupture')) {
      // Opt-out file exists, block future PRs
      await env.IDEMPOTENCY.put(
        `no-rupture:${repo}`,
        '1',
        { expirationTtl: 86400 * 365 } // 1 year
      );
    }
    
    if (commit.removed?.includes('.no-rupture')) {
      // Opt-out removed, allow PRs again
      await env.IDEMPOTENCY.delete(`no-rupture:${repo}`);
    }
  }
}

async function generateInstallUrl(env: Env): Promise<Response> {
  // Generate GitHub App manifest URL
  const manifest = {
    name: 'Rupture Migration Bot',
    url: 'https://ntoledo319.github.io/Rupture',
    callback_urls: ['https://ntoledo319.github.io/Rupture/pack/callback'],
    setup_url: 'https://ntoledo319.github.io/Rupture/pack/setup',
    webhook_url: 'https://rupture-worker.toledonick98.workers.dev/webhook/github',
    redirect_url: 'https://ntoledo319.github.io/Rupture/pack/installed',
    setup_on_install: true,
    default_permissions: {
      contents: 'write',
      pull_requests: 'write',
      metadata: 'read',
      checks: 'read',
    },
    default_events: [
      'push',
      'pull_request',
      'check_run',
      'installation',
      'installation_repositories',
    ],
  };
  
  const manifestJson = JSON.stringify(manifest);
  const manifestBase64 = btoa(manifestJson);
  
  const installUrl = `https://github.com/settings/apps/new?manifest=${encodeURIComponent(manifestBase64)}`;
  
  return new Response(JSON.stringify({
    installUrl,
    manifest,
  }), {
    headers: { 'Content-Type': 'application/json' },
  });
}

export async function createMigrationPR(
  installationId: string,
  repo: string,
  branchName: string,
  title: string,
  body: string,
  files: Array<{ path: string; content: string }>,
  env: Env
): Promise<{ prUrl: string; prNumber: number }> {
  // This would use GitHub API with the installation token
  // For now, return mock data
  console.log(`Creating PR on ${repo} from installation ${installationId}`);
  
  return {
    prUrl: `https://github.com/${repo}/pull/123`,
    prNumber: 123,
  };
}
