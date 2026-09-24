/**
 * Same-origin /api/* proxy for Cloudflare Pages (ADR 011/014). The browser only ever talks to the
 * Pages origin, so the HttpOnly SameSite=Lax cookies stay first-party and host-only.
 *
 * The API runs with CLIENT_IP_SOURCE=edge_header: it accepts a request only when it carries
 * EDGE_PROXY_SECRET and takes the client IP from X-Edge-Client-IP, which this proxy sets from
 * Cloudflare's CF-Connecting-IP (set by Cloudflare's edge, not by the client).
 */

export type ProxyEnv = { API_ORIGIN?: string; EDGE_PROXY_SECRET?: string }

// Client-supplied copies are removed so nothing downstream can trust a spoofed address.
const STRIPPED_REQUEST_HEADERS = [
  'host',
  'content-length',
  'x-edge-client-ip',
  'x-edge-proxy-secret',
  'x-forwarded-for',
  'x-real-ip',
  'forwarded',
]

function problem(status: number, detail: string): Response {
  return new Response(JSON.stringify({ type: 'about:blank', title: status === 404 ? 'Not Found' : 'Service Unavailable', status, detail }), {
    status,
    headers: { 'Content-Type': 'application/problem+json', 'Cache-Control': 'no-store' },
  })
}

export async function proxyToApi(request: Request, env: ProxyEnv): Promise<Response> {
  if (!env.API_ORIGIN || !env.EDGE_PROXY_SECRET || env.EDGE_PROXY_SECRET.length < 32) {
    return problem(503, 'The API proxy is not configured.')
  }
  const incoming = new URL(request.url)
  if (!incoming.pathname.startsWith('/api/')) return problem(404, 'Not found.')
  // Path-only join: the upstream origin is fixed by configuration, so this is never an open proxy.
  const target = new URL(incoming.pathname + incoming.search, env.API_ORIGIN)

  const headers = new Headers(request.headers)
  for (const name of STRIPPED_REQUEST_HEADERS) headers.delete(name)
  const clientIp = request.headers.get('cf-connecting-ip')
  if (clientIp) headers.set('X-Edge-Client-IP', clientIp)
  headers.set('X-Edge-Proxy-Secret', env.EDGE_PROXY_SECRET)
  // Small JSON responses: avoid re-encoding mismatches between edge and upstream compression.
  headers.set('Accept-Encoding', 'identity')

  const method = request.method.toUpperCase()
  const body = method === 'GET' || method === 'HEAD' ? undefined : await request.arrayBuffer()
  let upstream: Response
  try {
    upstream = await fetch(target, { method, headers, body, redirect: 'manual' })
  } catch {
    return problem(502, 'The API is unavailable.')
  }

  // Copying Headers keeps every Set-Cookie value; status and body pass through unchanged.
  const responseHeaders = new Headers(upstream.headers)
  responseHeaders.delete('content-encoding')
  responseHeaders.delete('content-length')
  responseHeaders.set('Cache-Control', 'no-store')
  return new Response(upstream.body, { status: upstream.status, statusText: upstream.statusText, headers: responseHeaders })
}
