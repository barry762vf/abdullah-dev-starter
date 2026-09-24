// @vitest-environment node
import { afterEach, describe, expect, it, vi } from 'vitest'
import { proxyToApi } from './_proxy'

const env = { API_ORIGIN: 'https://api.internal.example', EDGE_PROXY_SECRET: 's'.repeat(40) }
let seen: Request | null = null

function upstream(response: Response) {
  vi.stubGlobal('fetch', vi.fn(async (input: URL, init: RequestInit) => {
    seen = new Request(input, init)
    return response
  }))
}

afterEach(() => {
  vi.unstubAllGlobals()
  seen = null
})

describe('Pages /api proxy', () => {
  it('forwards method, path, query and body to the fixed API origin', async () => {
    upstream(new Response('{"ok":true}', { status: 201 }))
    const response = await proxyToApi(
      new Request('https://app.example.com/api/v1/auth/register?x=1', { method: 'POST', body: '{"a":1}', headers: { 'Content-Type': 'application/json' } }),
      env,
    )
    expect(response.status).toBe(201)
    expect(seen?.url).toBe('https://api.internal.example/api/v1/auth/register?x=1')
    expect(seen?.method).toBe('POST')
    expect(await seen?.text()).toBe('{"a":1}')
    expect(seen?.headers.get('content-type')).toBe('application/json')
  })

  it('authenticates itself and sets the client IP only from Cloudflare', async () => {
    upstream(new Response(null, { status: 204 }))
    await proxyToApi(
      new Request('https://app.example.com/api/v1/users/me', {
        headers: {
          'CF-Connecting-IP': '203.0.113.9',
          'X-Forwarded-For': '6.6.6.6',
          'X-Edge-Client-IP': '6.6.6.6',
          'X-Edge-Proxy-Secret': 'client-guess',
          'X-Real-IP': '6.6.6.6',
          Cookie: 'access_token=abc',
          'X-Requested-With': 'XMLHttpRequest',
        },
      }),
      env,
    )
    expect(seen?.headers.get('x-edge-client-ip')).toBe('203.0.113.9')
    expect(seen?.headers.get('x-edge-proxy-secret')).toBe(env.EDGE_PROXY_SECRET)
    expect(seen?.headers.get('x-forwarded-for')).toBeNull()
    expect(seen?.headers.get('x-real-ip')).toBeNull()
    expect(seen?.headers.get('cookie')).toBe('access_token=abc')
    expect(seen?.headers.get('x-requested-with')).toBe('XMLHttpRequest')
  })

  it('returns status, every Set-Cookie header and no-store', async () => {
    const headers = new Headers({ 'Content-Type': 'application/json', 'Cache-Control': 'public, max-age=60' })
    headers.append('Set-Cookie', 'access_token=a; HttpOnly; Secure; SameSite=Lax; Path=/api/v1')
    headers.append('Set-Cookie', 'refresh_token=r; HttpOnly; Secure; SameSite=Lax; Path=/api/v1/auth')
    upstream(new Response('{"detail":"x"}', { status: 401, headers }))
    const response = await proxyToApi(new Request('https://app.example.com/api/v1/auth/login', { method: 'POST', body: '{}' }), env)
    expect(response.status).toBe(401)
    expect(response.headers.getSetCookie()).toEqual([
      'access_token=a; HttpOnly; Secure; SameSite=Lax; Path=/api/v1',
      'refresh_token=r; HttpOnly; Secure; SameSite=Lax; Path=/api/v1/auth',
    ])
    expect(response.headers.get('cache-control')).toBe('no-store')
    expect(await response.text()).toBe('{"detail":"x"}')
  })

  it('passes redirects through instead of following them', async () => {
    upstream(new Response(null, { status: 307, headers: { Location: '/api/v1/other' } }))
    const response = await proxyToApi(new Request('https://app.example.com/api/v1/x'), env)
    expect(response.status).toBe(307)
    expect(response.headers.get('location')).toBe('/api/v1/other')
  })

  it('fails closed when misconfigured, outside /api, or when the API is down', async () => {
    upstream(new Response('unused'))
    expect((await proxyToApi(new Request('https://app.example.com/api/v1/x'), { API_ORIGIN: env.API_ORIGIN, EDGE_PROXY_SECRET: 'short' })).status).toBe(503)
    expect((await proxyToApi(new Request('https://app.example.com/api/v1/x'), {})).status).toBe(503)
    expect((await proxyToApi(new Request('https://app.example.com//evil.example/api/x'), env)).status).toBe(404)
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('network') }))
    const down = await proxyToApi(new Request('https://app.example.com/api/v1/x'), env)
    expect(down.status).toBe(502)
    expect(down.headers.get('content-type')).toBe('application/problem+json')
  })
})
