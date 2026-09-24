import { beforeEach, describe, expect, it } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'
import i18n from '../lib/i18n'
import { api, authTransport } from '../lib/api'
import { queryClient } from '../lib/queryClient'
import { App } from '../App'
import type { User } from '../types/auth'

const member: User = {
  id: 'u1', email: 'mona@example.com', full_name: 'Mona Member', is_active: true, is_verified: false,
  roles: ['user'], created_at: '2026-09-24T08:00:00Z',
}
const admin: User = { ...member, id: 'a1', email: 'ada@example.com', full_name: 'Ada Admin', roles: ['admin'] }

type Route = (config: InternalAxiosRequestConfig) => { status: number; data?: unknown }
let routes: Record<string, Route> = {}
let calls: { method: string; url: string; params?: Record<string, unknown> }[] = []

async function adapter(config: InternalAxiosRequestConfig): Promise<AxiosResponse> {
  const method = (config.method ?? 'get').toUpperCase()
  const url = String(config.url)
  calls.push({ method, url, params: config.params })
  const handler = routes[`${method} ${url}`] ?? routes[url]
  const { status, data } = handler ? handler(config) : { status: 404 }
  const response: AxiosResponse = { data: data ?? { status, detail: 'error' }, status, statusText: String(status), headers: {}, config }
  if (status >= 400) throw new AxiosError('failed', 'ERR_BAD_REQUEST', config, undefined, response)
  return response
}

function signedIn(user: User) {
  routes['/users/me'] = () => ({ status: 200, data: user })
}

function page<T>(items: T[], total = items.length, pageNumber = 1) {
  return { items, total, page: pageNumber, page_size: 20 }
}

function visit(path: string) {
  window.history.pushState({}, '', path)
  render(<App />)
}

beforeEach(async () => {
  queryClient.clear()
  window.localStorage.clear()
  document.documentElement.classList.remove('dark')
  routes = {}
  calls = []
  await i18n.changeLanguage('en')
  api.defaults.adapter = adapter
  authTransport.defaults.adapter = adapter
  Object.defineProperty(navigator, 'locks', { configurable: true, value: undefined })
})

describe('session propagation', () => {
  it('a sign-out broadcast from another tab clears this tab and leaves protected pages', async () => {
    signedIn(member)
    visit('/dashboard')
    expect(await screen.findByRole('heading', { name: 'Welcome back, Mona Member.' })).toBeInTheDocument()
    const otherTab = new BroadcastChannel('abdullah-kit-session')
    otherTab.postMessage('signed-out')
    otherTab.close()
    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/login')
  })

  it('ignores unknown or secret-looking cross-tab messages', async () => {
    signedIn(member)
    visit('/dashboard')
    await screen.findByRole('heading', { name: 'Welcome back, Mona Member.' })
    const otherTab = new BroadcastChannel('abdullah-kit-session')
    otherTab.postMessage({ type: 'signed-out', token: 'x' })
    otherTab.postMessage('delete-everything')
    otherTab.close()
    await new Promise((resolve) => setTimeout(resolve, 50))
    expect(window.location.pathname).toBe('/dashboard')
  })

  it('signs out from the navbar and returns protected pages to sign in', async () => {
    const user = userEvent.setup()
    signedIn(member)
    routes['POST /auth/logout'] = () => {
      routes['/users/me'] = () => ({ status: 401 })
      return { status: 204, data: '' }
    }
    visit('/dashboard')
    await user.click(await screen.findByRole('button', { name: 'Sign out' }))
    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument()
    expect(calls.some((call) => call.method === 'POST' && call.url === '/auth/logout')).toBe(true)
  })

  it('keeps the session and explains a failed sign-out', async () => {
    const user = userEvent.setup()
    signedIn(member)
    routes['POST /auth/logout'] = () => ({ status: 500 })
    visit('/dashboard')
    await user.click(await screen.findByRole('button', { name: 'Sign out' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not sign out. Please try again.')
    expect(window.location.pathname).toBe('/dashboard')
  })

  it('returns to an allowlisted admin page after login', async () => {
    const user = userEvent.setup()
    let authenticated = false
    routes['/users/me'] = () => (authenticated ? { status: 200, data: admin } : { status: 401 })
    routes['POST /auth/login'] = () => { authenticated = true; return { status: 200, data: admin } }
    routes['/admin/stats'] = () => ({ status: 200, data: { users_total: 1, users_active: 1, users_disabled: 0, users_verified: 0, active_sessions: 1, roles: [], generated_at: '2026-09-24T08:00:00Z' } })
    visit('/admin')
    await screen.findByRole('heading', { name: 'Welcome back' })
    await user.type(screen.getByLabelText('Email address'), 'ada@example.com')
    await user.type(screen.getByLabelText('Password'), 'Example-password-123!')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByText('Total accounts')).toBeInTheDocument()
    expect(window.location.pathname).toBe('/admin')
  })

  it('never redirects after login to a destination outside the allowlist', async () => {
    const user = userEvent.setup()
    routes['/users/me'] = () => ({ status: 401 })
    routes['POST /auth/login'] = () => {
      routes['/users/me'] = () => ({ status: 200, data: member })
      return { status: 200, data: member }
    }
    window.history.pushState({ usr: { from: '//evil.example/steal' }, key: 'x', idx: 0 }, '', '/login')
    render(<App />)
    await user.type(await screen.findByLabelText('Email address'), 'mona@example.com')
    await user.type(screen.getByLabelText('Password'), 'Example-password-123!')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    await waitFor(() => expect(window.location.pathname).toBe('/dashboard'))
  })
})

describe('shell preferences', () => {
  it('toggles dark theme and persists only the preference', async () => {
    const user = userEvent.setup()
    routes['/users/me'] = () => ({ status: 401 })
    visit('/')
    await user.click(await screen.findByRole('button', { name: 'Use dark theme' }))
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(window.localStorage.getItem('abdullah-kit-theme')).toBe('dark')
    const keys = Array.from({ length: window.localStorage.length }, (_, index) => window.localStorage.key(index))
    expect(keys.sort()).toEqual(['abdullah-kit-language', 'abdullah-kit-theme'])
    await user.click(screen.getByRole('button', { name: 'Use light theme' }))
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })
})

describe('administration states', () => {
  it('shows a retryable error when statistics fail, then the data', async () => {
    const user = userEvent.setup()
    signedIn(admin)
    let failures = 1
    routes['/admin/stats'] = () => (failures-- > 0 ? { status: 500 } : {
      status: 200,
      data: { users_total: 9, users_active: 9, users_disabled: 0, users_verified: 0, active_sessions: 2, roles: [], generated_at: '2026-09-24T08:00:00Z' },
    })
    visit('/admin')
    await user.click(await screen.findByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('Total accounts')).toBeInTheDocument()
    expect(screen.getAllByText('9')).toHaveLength(2) // total and active
    expect(calls.filter((call) => call.url === '/admin/stats')).toHaveLength(2)
  })

  it('shows the RoleGuard error state (not access denied) when the profile cannot load', async () => {
    routes['/users/me'] = () => ({ status: 500 })
    visit('/admin')
    expect(await screen.findByRole('heading', { name: 'Something went wrong' })).toBeInTheDocument()
    expect(screen.queryByText('Access denied')).not.toBeInTheDocument()
  })

  it('shows empty and error states for the audit log and users', async () => {
    signedIn(admin)
    routes['/admin/audit-logs'] = () => ({ status: 200, data: page([]) })
    visit('/admin/audit-logs')
    expect(await screen.findByText('No audit events')).toBeInTheDocument()
    routes['/admin/users'] = () => ({ status: 500 })
    window.history.pushState({}, '', '/admin/users')
    window.dispatchEvent(new PopStateEvent('popstate'))
    expect(await screen.findByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })

  it('pages through users with a mirrored, labelled pagination control', async () => {
    const user = userEvent.setup()
    signedIn(admin)
    routes['/admin/users'] = (config) => {
      const pageNumber = Number(config.params?.page ?? 1)
      return { status: 200, data: page([{ ...member, id: `u${pageNumber}`, full_name: `Person ${pageNumber}` }], 45, pageNumber) }
    }
    visit('/admin/users')
    const pager = await screen.findByRole('navigation', { name: 'Users pages' })
    expect(within(pager).getByText('Page 1 of 3 · 45 total')).toBeInTheDocument()
    expect(within(pager).getByRole('button', { name: 'Previous' })).toBeDisabled()
    await user.click(within(pager).getByRole('button', { name: 'Next' }))
    expect(await screen.findByText('Person 2')).toBeInTheDocument()
    expect(calls.filter((call) => call.url === '/admin/users').at(-1)?.params?.page).toBe(2)
  })

  it('enables a disabled user without a confirmation step and reports refused changes', async () => {
    const user = userEvent.setup()
    signedIn(admin)
    const disabled = { ...member, is_active: false }
    routes['/admin/users'] = () => ({ status: 200, data: page([disabled]) })
    routes[`PATCH /admin/users/${disabled.id}`] = () => ({ status: 404 })
    visit('/admin/users')
    await user.click(await screen.findByRole('button', { name: 'Enable Mona Member' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(await screen.findByRole('alert')).toHaveTextContent('This account no longer exists.')
  })

  it('keeps keyboard focus inside the confirmation dialog and restores it on Escape', async () => {
    const user = userEvent.setup()
    signedIn(admin)
    routes['/admin/users'] = () => ({ status: 200, data: page([member]) })
    visit('/admin/users')
    const trigger = await screen.findByRole('button', { name: 'Disable Mona Member' })
    await user.click(trigger)
    const dialog = screen.getByRole('dialog', { name: 'Disable this account?' })
    for (let press = 0; press < 5; press += 1) {
      await user.tab()
      expect(dialog).toContainElement(document.activeElement as HTMLElement)
    }
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
  })
})
