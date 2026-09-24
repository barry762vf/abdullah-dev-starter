import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'
import { API_BASE_PATH, ApiError, api, authTransport, ensureSession, login, logout, subscribeSession, toApiError } from '../lib/api'
import type { User } from '../types/auth'

const user: User = {
  id: '00000000-0000-0000-0000-000000000001', email: 'person@example.test', full_name: 'Person',
  is_active: true, is_verified: false, roles: ['user'], created_at: '2026-09-24T00:00:00Z',
}

function response(config: InternalAxiosRequestConfig, status: number, data: unknown): AxiosResponse {
  return { config, status, statusText: status === 401 ? 'Unauthorized' : 'OK', headers: {}, data }
}

function unauthorized(config: InternalAxiosRequestConfig): AxiosError {
  return new AxiosError('Unauthorized', 'ERR_BAD_REQUEST', config, undefined, response(config, 401, { detail: 'Unauthorized' }))
}

beforeEach(() => {
  vi.restoreAllMocks()
  window.localStorage.clear()
  Object.defineProperty(navigator, 'locks', {
    configurable: true,
    value: { request: (_name: string, operation: () => Promise<unknown>) => operation() },
  })
})

describe('API contract', () => {
  it('uses one relative API base, JSON requests and cookie credentials', async () => {
    expect(API_BASE_PATH).toBe('/api/v1')
    expect(api.defaults.baseURL).toBe('/api/v1')
    expect(api.defaults.withCredentials).toBe(true)
    let seen: InternalAxiosRequestConfig | undefined
    api.defaults.adapter = async (config) => { seen = config; return response(config, 200, { status: 'healthy' }) }
    await api.get('/health')
    expect(seen?.url).toBe('/health')
    expect(seen?.headers.get('X-Requested-With')).toBe('XMLHttpRequest')
    expect(seen?.baseURL).toBe('/api/v1')
  })

  it('normalizes RFC 7807 details and validation errors', () => {
    const config = { headers: {} } as InternalAxiosRequestConfig
    const error = new AxiosError('Bad Request', 'ERR_BAD_REQUEST', config, undefined, response(config, 422, {
      type: 'about:blank', title: 'Unprocessable Entity', status: 422, detail: 'Request validation failed.',
      request_id: 'req-42', errors: [{ location: ['body', 'email'], message: 'Invalid', type: 'value_error' }],
    }))
    const result = toApiError(error)
    expect(result).toBeInstanceOf(ApiError)
    expect(result.status).toBe(422)
    expect(result.message).toBe('Request validation failed.')
    expect(result.requestId).toBe('req-42')
    expect(result.errors).toHaveLength(1)
  })

  it('serializes simultaneous refresh needs and never stores tokens', async () => {
    let checks = 0
    let refreshes = 0
    const store = vi.spyOn(window.localStorage, 'setItem')
    authTransport.defaults.adapter = async (config) => {
      if (config.url === '/users/me') {
        checks += 1
        if (checks === 1) throw unauthorized(config)
        return response(config, 200, user)
      }
      if (config.url === '/auth/refresh') { refreshes += 1; return response(config, 200, user) }
      throw Error('unexpected route')
    }
    await Promise.all([ensureSession(), ensureSession()])
    expect(refreshes).toBe(1)
    expect(checks).toBe(1)
    await ensureSession()
    expect(refreshes).toBe(1)
    expect(checks).toBe(2)
    expect(store).not.toHaveBeenCalled()
  })

  it('does not retry refresh after an ambiguous network failure', async () => {
    let refreshes = 0
    authTransport.defaults.adapter = async (config) => {
      if (config.url === '/users/me') throw unauthorized(config)
      if (config.url === '/auth/refresh') { refreshes += 1; throw new AxiosError('Network Error', 'ERR_NETWORK', config) }
      throw Error('unexpected route')
    }
    await expect(ensureSession()).rejects.toMatchObject({ status: 401 })
    await expect(ensureSession()).rejects.toMatchObject({ status: 401 })
    expect(refreshes).toBe(1)
  })

  it('requires re-login rather than unsafe automatic refresh without Web Locks', async () => {
    Object.defineProperty(navigator, 'locks', { configurable: true, value: undefined })
    await expect(ensureSession()).rejects.toMatchObject({ status: 401 })
  })

  it('login returns the profile without writing credentials to browser storage', async () => {
    const store = vi.spyOn(window.localStorage, 'setItem')
    authTransport.defaults.adapter = async (config) => response(config, 200, user)
    await expect(login({ email: user.email, password: 'Example-password-123!' })).resolves.toEqual(user)
    expect(store).not.toHaveBeenCalled()
  })

  it('broadcasts only a state signal after successful logout', async () => {
    const signals: string[] = []
    const unsubscribe = subscribeSession((signal) => signals.push(signal))
    const store = vi.spyOn(window.localStorage, 'setItem')
    authTransport.defaults.adapter = async (config) => response(config, 204, '')
    await logout()
    unsubscribe()
    expect(signals).toEqual(['signed-out'])
    expect(store).not.toHaveBeenCalled()
  })

  it('serializes login, refresh and logout on one Web Lock; a refresh queued behind logout aborts', async () => {
    vi.resetModules()
    const fresh = await import('../lib/api')
    const lockNames: string[] = []
    let tail: Promise<unknown> = Promise.resolve()
    Object.defineProperty(navigator, 'locks', {
      configurable: true,
      value: {
        // Minimal exclusive lock: each operation starts after the previous one settles.
        request: (name: string, operation: () => Promise<unknown>) => {
          lockNames.push(name)
          const run = tail.then(operation, operation)
          tail = run.catch(() => undefined)
          return run
        },
      },
    })
    const routes: string[] = []
    fresh.authTransport.defaults.adapter = async (config) => {
      routes.push(String(config.url))
      if (config.url === '/auth/login') return response(config, 200, user)
      if (config.url === '/auth/logout') return response(config, 204, '')
      throw Error('unexpected route')
    }
    await fresh.login({ email: user.email, password: 'Example-password-123!' })
    const signingOut = fresh.logout()
    const queuedRefresh = fresh.ensureSession()
    await signingOut
    await expect(queuedRefresh).rejects.toMatchObject({ status: 401 })
    expect(new Set(lockNames)).toEqual(new Set(['abdullah-auth-session']))
    expect(lockNames).toHaveLength(3)
    // The queued refresh observed the sign-out and made no /users/me or /auth/refresh call.
    expect(routes).toEqual(['/auth/login', '/auth/logout'])
  })

  it('retries the original request once after refresh and never intercepts auth routes', async () => {
    vi.resetModules()
    const fresh = await import('../lib/api')
    let refreshed = false
    const calls: string[] = []
    fresh.authTransport.defaults.adapter = async (config) => {
      calls.push(`auth:${config.url}`)
      if (config.url === '/users/me' && !refreshed) throw unauthorized(config)
      if (config.url === '/auth/refresh') { refreshed = true; return response(config, 200, user) }
      return response(config, 200, user)
    }
    fresh.api.defaults.adapter = async (config) => {
      calls.push(`api:${config.url}`)
      if (config.url === '/auth/anything' || !refreshed) throw unauthorized(config)
      return response(config, 200, { ok: true })
    }
    await expect(fresh.apiRequest({ url: '/items' })).resolves.toEqual({ ok: true })
    expect(calls).toEqual(['api:/items', 'auth:/users/me', 'auth:/auth/refresh', 'api:/items'])
    calls.length = 0
    await expect(fresh.apiRequest({ url: '/auth/anything' })).rejects.toMatchObject({ status: 401 })
    expect(calls).toEqual(['api:/auth/anything'])
  })

  it('broadcasts only non-secret state names and bounds session request time', async () => {
    vi.resetModules()
    const posted: unknown[] = []
    vi.spyOn(BroadcastChannel.prototype, 'postMessage').mockImplementation((message: unknown) => { posted.push(message) })
    const fresh = await import('../lib/api')
    fresh.authTransport.defaults.adapter = async (config) => {
      if (config.url === '/users/me') throw unauthorized(config)
      if (config.url === '/auth/refresh') throw new AxiosError('timeout of 20000ms exceeded', 'ECONNABORTED', config)
      return response(config, 200, user)
    }
    await fresh.login({ email: user.email, password: 'Example-password-123!' })
    await expect(fresh.ensureSession()).rejects.toMatchObject({ status: 401 })
    expect(fresh.authTransport.defaults.timeout).toBe(fresh.AUTH_TIMEOUT_MS)
    expect(posted).toEqual(['auth-updated', 'refresh-uncertain'])
    expect(posted.every((message) => typeof message === 'string')).toBe(true)
  })

  it('treats a known refresh 401 as sign-out without retrying', async () => {
    const signals: string[] = []
    const unsubscribe = subscribeSession((signal) => signals.push(signal))
    let refreshes = 0
    authTransport.defaults.adapter = async (config) => {
      if (config.url === '/users/me') throw unauthorized(config)
      if (config.url === '/auth/refresh') { refreshes += 1; throw unauthorized(config) }
      throw Error('unexpected route')
    }
    await expect(ensureSession()).rejects.toMatchObject({ status: 401 })
    unsubscribe()
    expect(refreshes).toBe(1)
    expect(signals).toContain('signed-out')
  })
})
