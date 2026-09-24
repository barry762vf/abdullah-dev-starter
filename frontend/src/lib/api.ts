import axios, { type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios'
import type { LoginInput, RegisterInput, User } from '../types/auth'

export const API_BASE_PATH = '/api/v1'
const config = {
  baseURL: API_BASE_PATH,
  withCredentials: true,
  headers: { 'X-Requested-With': 'XMLHttpRequest' },
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly requestId?: string,
    public readonly errors?: unknown[],
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

type ProblemDetails = {
  title?: string
  detail?: string
  status?: number
  request_id?: string
  errors?: unknown[]
}

export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error
  if (axios.isAxiosError(error)) {
    const body = error.response?.data
    const problem: ProblemDetails | null = body && typeof body === 'object' ? body : null
    return new ApiError(
      typeof problem?.detail === 'string' ? problem.detail : 'The request could not be completed.',
      error.response?.status ?? 0,
      typeof problem?.request_id === 'string' ? problem.request_id : undefined,
      Array.isArray(problem?.errors) ? problem.errors : undefined,
    )
  }
  return new ApiError('The request could not be completed.', 0)
}

type SessionSignal = 'auth-updated' | 'signed-out' | 'refresh-uncertain'
const SESSION_EVENT = 'abdullah-kit-session'
const channel = typeof BroadcastChannel === 'undefined' ? null : new BroadcastChannel(SESSION_EVENT)
let signOutGeneration = 0
let refreshUncertain = false
let refreshPromise: Promise<void> | null = null

function receiveSignal(signal: SessionSignal): void {
  if (signal === 'signed-out') signOutGeneration += 1
  if (signal === 'refresh-uncertain') refreshUncertain = true
  if (signal === 'auth-updated' || signal === 'signed-out') refreshUncertain = false
  window.dispatchEvent(new CustomEvent<SessionSignal>(SESSION_EVENT, { detail: signal }))
}

channel?.addEventListener('message', (event: MessageEvent<SessionSignal>) => {
  if (event.data === 'auth-updated' || event.data === 'signed-out' || event.data === 'refresh-uncertain') receiveSignal(event.data)
})

function emitSignal(signal: SessionSignal): void {
  receiveSignal(signal)
  channel?.postMessage(signal)
}

export function subscribeSession(listener: (signal: SessionSignal) => void): () => void {
  const onEvent = (event: Event) => listener((event as CustomEvent<SessionSignal>).detail)
  window.addEventListener(SESSION_EVENT, onEvent)
  return () => window.removeEventListener(SESSION_EVENT, onEvent)
}

// Session calls run while holding the cross-tab Web Lock; a hung request must not block every tab.
// A timed-out refresh is handled as an ambiguous failure and is never retried automatically.
export const AUTH_TIMEOUT_MS = 20_000

// This instance has no refresh interceptor. A failed refresh must never recursively retry itself.
export const authTransport = axios.create({ ...config, timeout: AUTH_TIMEOUT_MS })
export const api = axios.create(config)

function isUnauthorized(error: unknown): boolean {
  return axios.isAxiosError(error) && error.response?.status === 401
}

async function withSessionLock<T>(operation: () => Promise<T>): Promise<T> {
  if (!navigator.locks) return operation()
  return navigator.locks.request('abdullah-auth-session', operation)
}

async function refreshUnderLock(observedGeneration: number): Promise<void> {
  if (observedGeneration !== signOutGeneration) throw new ApiError('Session ended.', 401)
  if (refreshUncertain) throw new ApiError('Sign in again to continue.', 401)

  try {
    await authTransport.get<User>('/users/me')
    return // Another tab already refreshed the shared cookie.
  } catch (error) {
    if (!isUnauthorized(error)) throw toApiError(error)
  }

  try {
    await authTransport.post<User>('/auth/refresh')
    emitSignal('auth-updated')
  } catch (error) {
    if (isUnauthorized(error)) {
      emitSignal('signed-out')
      throw toApiError(error)
    }
    // The server may have committed rotation before the response was lost.
    emitSignal('refresh-uncertain')
    try {
      await authTransport.get<User>('/users/me')
      refreshUncertain = false
      emitSignal('auth-updated')
      return
    } catch {
      throw new ApiError('Could not confirm your session. Sign in again.', 401)
    }
  }
}

export function ensureSession(): Promise<void> {
  if (refreshPromise) return refreshPromise
  if (!navigator.locks) return Promise.reject(new ApiError('Sign in again to continue.', 401))
  const observedGeneration = signOutGeneration
  refreshPromise = withSessionLock(() => refreshUnderLock(observedGeneration)).finally(() => {
    refreshPromise = null
  })
  return refreshPromise
}

type RetriedRequest = InternalAxiosRequestConfig & { _sessionRetried?: boolean }

api.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      const request = error.config as RetriedRequest | undefined
      if (request && !request._sessionRetried && !request.url?.startsWith('/auth/')) {
        request._sessionRetried = true
        try {
          await ensureSession()
          return api.request(request)
        } catch (sessionError) {
          return Promise.reject(toApiError(sessionError))
        }
      }
    }
    return Promise.reject(toApiError(error))
  },
)

export async function getCurrentUser(signal?: AbortSignal): Promise<User> {
  const response = await api.get<User>('/users/me', { signal })
  return response.data
}

export async function login(input: LoginInput): Promise<User> {
  try {
    // Signal before releasing the lock so a queued session operation sees the new state.
    const response = await withSessionLock(async () => {
      const result = await authTransport.post<User>('/auth/login', input)
      refreshUncertain = false
      emitSignal('auth-updated')
      return result
    })
    return response.data
  } catch (error) {
    throw toApiError(error)
  }
}

export async function register(input: RegisterInput): Promise<User> {
  try {
    const response = await authTransport.post<User>('/auth/register', input)
    return response.data
  } catch (error) {
    throw toApiError(error)
  }
}

export async function logout(): Promise<void> {
  try {
    // Broadcast while holding the lock: a refresh queued here or in another tab must observe it.
    await withSessionLock(async () => {
      await authTransport.post('/auth/logout')
      refreshUncertain = false
      emitSignal('signed-out')
    })
  } catch (error) {
    throw toApiError(error)
  }
}

export async function apiRequest<T>(request: AxiosRequestConfig): Promise<T> {
  const response = await api.request<T>(request)
  return response.data
}
