import { beforeEach, describe, expect, it } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'
import i18n from '../lib/i18n'
import { api, authTransport } from '../lib/api'
import { queryClient } from '../lib/queryClient'
import { App } from '../App'
import type { User } from '../types/auth'

function person(id: string, name: string, roles: string[], extra: Partial<User> = {}): User {
  return {
    id, email: `${name.toLowerCase().replace(' ', '.')}@example.com`, full_name: name, is_active: true,
    is_verified: false, roles, created_at: '2026-09-24T08:00:00Z', ...extra,
  }
}

const admin = person('a0', 'Ada Admin', ['admin'])
const root = person('s0', 'Sam Root', ['superadmin'])
const member = person('u1', 'Mona Member', ['user'])
const otherAdmin = person('a1', 'Omar Admin', ['admin'])
const hostileAgent = '<img src=x onerror="window.__xss=1"><script>window.__xss=1</script>'

type Call = { method: string; url: string; params?: Record<string, unknown>; data?: unknown }
let calls: Call[] = []
let current: User | null = null
let patchStatus = 200
let usersPage: User[] = []

function reply(config: InternalAxiosRequestConfig, status: number, data: unknown): AxiosResponse {
  if (status >= 400) {
    const response = { data: { status, detail: 'error' }, status, statusText: 'Error', headers: {}, config }
    throw new AxiosError('Request failed', 'ERR_BAD_REQUEST', config, undefined, response)
  }
  return { data, status, statusText: 'OK', headers: {}, config }
}

async function adapter(config: InternalAxiosRequestConfig): Promise<AxiosResponse> {
  const url = String(config.url)
  const method = (config.method ?? 'get').toUpperCase()
  calls.push({ method, url, params: config.params, data: config.data ? JSON.parse(String(config.data)) : undefined })
  if (url === '/users/me') return current ? reply(config, 200, current) : reply(config, 401, null)
  if (url === '/admin/stats') {
    return reply(config, 200, {
      users_total: 12, users_active: 10, users_disabled: 2, users_verified: 4, active_sessions: 7,
      roles: [{ name: 'admin', users: 2 }, { name: 'superadmin', users: 1 }, { name: 'user', users: 9 }],
      generated_at: '2026-09-24T08:00:00Z',
    })
  }
  if (url === '/admin/users' && method === 'GET') {
    return reply(config, 200, { items: usersPage, total: usersPage.length, page: 1, page_size: 20 })
  }
  if (url.startsWith('/admin/users/') && method === 'PATCH') {
    const target = usersPage.find((user) => url.endsWith(user.id))!
    return reply(config, patchStatus, { ...target, ...JSON.parse(String(config.data)) })
  }
  if (url === '/admin/audit-logs') {
    return reply(config, 200, {
      items: [{
        id: 'l1', created_at: '2026-09-24T08:00:00Z', action: 'auth.login_failed', entity: 'user', entity_id: null,
        actor: null, ip_address: '203.0.113.9', user_agent: hostileAgent, details: { note: '<b>not html</b>' },
      }],
      total: 1, page: 1, page_size: 20,
    })
  }
  throw new Error(`unexpected ${method} ${url}`)
}

function adminCalls() {
  return calls.filter((call) => call.url.startsWith('/admin'))
}

beforeEach(async () => {
  queryClient.clear()
  window.localStorage.clear()
  calls = []
  current = null
  patchStatus = 200
  usersPage = [admin, member, otherAdmin]
  await i18n.changeLanguage('en')
  api.defaults.adapter = adapter
  authTransport.defaults.adapter = adapter
  Object.defineProperty(navigator, 'locks', { configurable: true, value: undefined })
})

function visit(path: string) {
  window.history.pushState({}, '', path)
  render(<App />)
}

describe('administration', () => {
  it('shows access denied to a signed-in non-admin and never calls the admin API', async () => {
    current = member
    visit('/admin/users')
    expect(await screen.findByRole('heading', { level: 1, name: 'Access denied' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Administration' })).not.toBeInTheDocument()
    expect(adminCalls()).toEqual([])
  })

  it('sends signed-out visitors to sign in', async () => {
    visit('/admin')
    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/login')
  })

  it('shows admins the navigation link and statistics, including in Arabic RTL', async () => {
    current = admin
    visit('/admin')
    expect(await screen.findByText('Total accounts')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Administration' })).toBeInTheDocument()
    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.getByText('Active sessions')).toBeInTheDocument()
    await i18n.changeLanguage('ar')
    expect(await screen.findByRole('heading', { level: 1, name: 'الإدارة' })).toBeInTheDocument()
    expect(document.documentElement.dir).toBe('rtl')
    expect(screen.getByText('إجمالي الحسابات')).toBeInTheDocument()
    expect(screen.getByText('مشرف عام')).toBeInTheDocument()
  })

  it('lets an admin disable an ordinary user only after confirmation', async () => {
    const user = userEvent.setup()
    current = admin
    visit('/admin/users')
    const table = await screen.findByRole('table')
    const rows = within(table).getAllByRole('row')
    // Admins get no role selector, and no actions on themselves or on other administrators.
    expect(within(table).queryByRole('combobox')).not.toBeInTheDocument()
    expect(within(rows[1]).getByText('No actions available')).toBeInTheDocument()
    expect(within(rows[3]).getByText('No actions available')).toBeInTheDocument()

    await user.click(within(table).getByRole('button', { name: 'Disable Mona Member' }))
    const dialog = screen.getByRole('dialog', { name: 'Disable this account?' })
    expect(calls.some((call) => call.method === 'PATCH')).toBe(false)
    await user.click(within(dialog).getByRole('button', { name: 'Disable' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(calls.find((call) => call.method === 'PATCH')).toMatchObject({ url: '/admin/users/u1', data: { is_active: false } })
  })

  it('lets a superadmin change a role with confirmation and explains a refused change', async () => {
    const user = userEvent.setup()
    current = root
    usersPage = [root, member]
    visit('/admin/users')
    const select = await screen.findByRole('combobox', { name: 'Role for Mona Member' })
    await user.selectOptions(select, 'admin')
    const dialog = screen.getByRole('dialog', { name: 'Change role?' })
    expect(within(dialog).getByText(/from User to Admin/)).toBeInTheDocument()
    patchStatus = 409
    await user.click(within(dialog).getByRole('button', { name: 'Change role' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('At least one active superadmin must remain.')
    expect(calls.find((call) => call.method === 'PATCH')?.data).toEqual({ roles: ['admin'] })
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('debounces search and shows the empty state', async () => {
    const user = userEvent.setup()
    current = admin
    visit('/admin/users')
    await screen.findByRole('table')
    usersPage = []
    await user.type(screen.getByLabelText('Search'), 'zz')
    expect(await screen.findByText('No users found')).toBeInTheDocument()
    const searches = adminCalls().filter((call) => call.url === '/admin/users').map((call) => call.params?.search)
    expect(searches).toEqual([undefined, 'zz'])
  })

  it('renders hostile audit data as inert text', async () => {
    const user = userEvent.setup()
    current = admin
    visit('/admin/audit-logs')
    const table = await screen.findByRole('table')
    expect(within(table).getByText(hostileAgent)).toBeInTheDocument()
    expect(document.querySelector('img, script:not([src])')).toBeNull()
    await user.click(within(table).getByRole('button', { name: 'Details for auth.login_failed' }))
    const dialog = screen.getByRole('dialog', { name: 'Audit event' })
    expect(within(dialog).getByText(/<b>not html<\/b>/)).toBeInTheDocument()
    expect(dialog.querySelector('b')).toBeNull()
    expect((window as unknown as { __xss?: number }).__xss).toBeUndefined()
  })
})
