/**
 * R2 upload handling for audit file uploads
 * Issues presigned URLs for secure direct-to-R2 uploads
 */

import type { Env } from './index';

const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
const ALLOWED_EXTENSIONS = ['.yaml', '.yml', '.json', '.tf', '.js', '.ts', '.py', '.txt'];

export async function uploadHandler(request: Request, env: Env, path: string): Promise<Response> {
  if (path === '/upload/presign' && request.method === 'POST') {
    return generatePresignedUrl(request, env);
  }
  
  if (path.startsWith('/upload/') && request.method === 'GET') {
    return serveUploadedFile(request, env, path);
  }
  
  return new Response('Not found', { status: 404 });
}

async function generatePresignedUrl(request: Request, env: Env): Promise<Response> {
  const body = await request.json() as {
    filename: string;
    contentType?: string;
    size?: number;
  };
  
  // Validate filename
  const extension = body.filename.toLowerCase().slice(body.filename.lastIndexOf('.'));
  if (!ALLOWED_EXTENSIONS.includes(extension)) {
    return new Response(JSON.stringify({
      error: 'Invalid file type',
      allowed: ALLOWED_EXTENSIONS,
    }), { status: 400, headers: { 'Content-Type': 'application/json' } });
  }
  
  // Validate size
  if (body.size && body.size > MAX_FILE_SIZE) {
    return new Response(JSON.stringify({
      error: 'File too large',
      maxSize: MAX_FILE_SIZE,
    }), { status: 400, headers: { 'Content-Type': 'application/json' } });
  }
  
  // Generate unique upload ID
  const uploadId = crypto.randomUUID();
  const key = `uploads/${uploadId}/${body.filename}`;
  
  // Store upload metadata
  const metadata = {
    filename: body.filename,
    contentType: body.contentType || 'application/octet-stream',
    size: body.size,
    uploadedAt: new Date().toISOString(),
    expiresAt: new Date(Date.now() + 3600 * 1000).toISOString(), // 1 hour
  };
  
  await env.IDEMPOTENCY.put(`upload:${uploadId}`, JSON.stringify(metadata), {
    expirationTtl: 3600, // 1 hour
  });
  
  // In production, this would generate a presigned R2 URL
  // For now, return the upload endpoint
  return new Response(JSON.stringify({
    uploadId,
    uploadUrl: `/upload/${uploadId}`,
    expiresIn: 3600,
    maxSize: MAX_FILE_SIZE,
  }), {
    headers: { 'Content-Type': 'application/json' },
  });
}

async function serveUploadedFile(request: Request, env: Env, path: string): Promise<Response> {
  const uploadId = path.replace('/upload/', '');
  
  // Check if upload exists
  const metadata = await env.IDEMPOTENCY.get(`upload:${uploadId}`);
  if (!metadata) {
    return new Response('Upload not found or expired', { status: 404 });
  }
  
  if (request.method === 'PUT') {
    // Handle file upload
    const object = await request.arrayBuffer();
    
    // Store in R2
    const key = `uploads/${uploadId}/file`;
    await env.UPLOADS.put(key, object);
    
    // Update metadata
    const meta = JSON.parse(metadata);
    meta.received = true;
    meta.receivedAt = new Date().toISOString();
    await env.IDEMPOTENCY.put(`upload:${uploadId}`, JSON.stringify(meta));
    
    return new Response(JSON.stringify({
      success: true,
      uploadId,
    }), {
      headers: { 'Content-Type': 'application/json' },
    });
  }
  
  if (request.method === 'GET') {
    // Retrieve uploaded file
    const key = `uploads/${uploadId}/file`;
    const object = await env.UPLOADS.get(key);
    
    if (!object) {
      return new Response('File not found', { status: 404 });
    }
    
    const meta = JSON.parse(metadata);
    
    return new Response(object.body, {
      headers: {
        'Content-Type': meta.contentType || 'application/octet-stream',
        'Content-Disposition': `attachment; filename="${meta.filename}"`,
      },
    });
  }
  
  return new Response('Method not allowed', { status: 405 });
}

export async function cleanupOldUploads(env: Env): Promise<void> {
  // List all uploads in R2
  const uploads = await env.UPLOADS.list({ prefix: 'uploads/' });
  
  const now = Date.now();
  const thirtyDaysMs = 30 * 24 * 60 * 60 * 1000;
  
  for (const object of uploads.objects || []) {
    // Check upload age from metadata
    const uploadId = object.key.split('/')[1];
    const metadata = await env.IDEMPOTENCY.get(`upload:${uploadId}`);
    
    if (metadata) {
      const meta = JSON.parse(metadata);
      const uploadedAt = new Date(meta.uploadedAt).getTime();
      
      if (now - uploadedAt > thirtyDaysMs) {
        // Delete old upload
        await env.UPLOADS.delete(object.key);
        await env.IDEMPOTENCY.delete(`upload:${uploadId}`);
        console.log(`Cleaned up old upload: ${uploadId}`);
      }
    }
  }
}
