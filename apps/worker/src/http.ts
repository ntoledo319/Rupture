export function jsonResponse(body: unknown, status = 200, headers: HeadersInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      ...headers,
    },
  });
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export async function readBody(request: Request): Promise<Record<string, unknown>> {
  const contentType = request.headers.get('Content-Type') || '';

  if (contentType.includes('application/json')) {
    const body = await request.json();
    return isRecord(body) ? body : {};
  }

  if (
    contentType.includes('application/x-www-form-urlencoded') ||
    contentType.includes('multipart/form-data')
  ) {
    const form = await request.formData();
    const body: Record<string, unknown> = {};
    for (const [key, value] of form.entries()) {
      body[key] = value;
    }
    return body;
  }

  return {};
}

export function stringField(
  body: Record<string, unknown>,
  field: string
): string | undefined {
  const value = body[field];
  return typeof value === 'string' && value.trim() ? value.trim() : undefined;
}

export function wantsHtmlRedirect(request: Request): boolean {
  const accept = request.headers.get('Accept') || '';
  const contentType = request.headers.get('Content-Type') || '';
  return (
    accept.includes('text/html') ||
    contentType.includes('application/x-www-form-urlencoded') ||
    contentType.includes('multipart/form-data')
  );
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export async function hmacSha256Hex(secret: string, payload: string): Promise<string> {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  const signature = await crypto.subtle.sign('HMAC', key, encoder.encode(payload));
  return Array.from(new Uint8Array(signature))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

export function timingSafeEqualHex(a: string, b: string): boolean {
  if (a.length !== b.length) return false;

  let result = 0;
  for (let i = 0; i < a.length; i++) {
    result |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return result === 0;
}
