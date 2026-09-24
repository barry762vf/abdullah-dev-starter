import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'
import i18n from '../lib/i18n'
import { api, authTransport } from '../lib/api'
import { queryClient } from '../lib/queryClient'
import { App } from '../App'

const profile = {
  id: '00000000-0000-0000-0000-000000000001', email: 'person@example.test', full_name: 'Example Person',
  is_active: true, is_verified: false, roles: ['user'], created_at: '2026-09-24T00:00:00Z',
}

function unauthorized(config: InternalAxiosRequestConfig): AxiosError {
  const response: AxiosResponse = { data: { detail: 'Unauthorized' }, status: 401, statusText: 'Unauthorized', headers: {}, config }
  return new AxiosError('Unauthorized', 'ERR_BAD_REQUEST', config, undefined, response)
}

beforeEach(async () => {
  queryClient.clear()
  window.localStorage.clear()
  window.history.pushState({}, '', '/')
  await i18n.changeLanguage('en')
  api.defaults.adapter = async (config) => { throw unauthorized(config) }
  authTransport.defaults.adapter = async (config) => { throw unauthorized(config) }
  Object.defineProperty(navigator, 'locks', { configurable: true, value: undefined })
})

describe('frontend shell', () => {
  it('renders English with LTR direction and core navigation', async () => {
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'A calm foundation for your next idea.' })).toBeInTheDocument()
    expect(document.documentElement.lang).toBe('en')
    expect(document.documentElement.dir).toBe('ltr')
    expect(screen.getByRole('navigation', { name: 'Workspace' })).toBeInTheDocument()
    expect(screen.getByRole('main')).toBeInTheDocument()
  })

  it('switches to Arabic, mirrors the root, and persists the language', async () => {
    const user = userEvent.setup()
    render(<App />)
    // The accessible name contains the visible target-language label (WCAG label-in-name).
    const toArabic = screen.getByRole('button', { name: 'Language: العربية' })
    expect(within(toArabic).getByText('العربية')).toHaveAttribute('lang', 'ar')
    await user.click(toArabic)
    expect(await screen.findByRole('heading', { name: 'أساس هادئ لفكرتك القادمة.' })).toBeInTheDocument()
    expect(document.documentElement.lang).toBe('ar')
    expect(document.documentElement.dir).toBe('rtl')
    expect(window.localStorage.getItem('abdullah-kit-language')).toBe('ar')
    expect(screen.getByRole('navigation', { name: 'مساحة العمل' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'اللغة: English' }))
    expect(document.documentElement.dir).toBe('ltr')
  })

  it('applies a saved Arabic direction when i18n loads, before React renders', async () => {
    document.documentElement.lang = 'en'
    document.documentElement.dir = 'ltr'
    window.localStorage.setItem('abdullah-kit-language', 'ar')
    vi.resetModules()
    await import('../lib/i18n')
    expect(document.documentElement.lang).toBe('ar')
    expect(document.documentElement.dir).toBe('rtl')
  })

  it('opens the mobile menu as a keyboard-accessible dialog', async () => {
    const user = userEvent.setup()
    render(<App />)
    const menuButton = screen.getByRole('button', { name: 'Open menu' })
    expect(menuButton).toHaveAttribute('aria-expanded', 'false')
    await user.click(menuButton)
    const dialog = screen.getByRole('dialog', { name: 'Workspace' })
    expect(menuButton).toHaveAttribute('aria-expanded', 'true')
    expect(within(dialog).getByRole('button', { name: 'Close menu' })).toHaveFocus()
    await user.keyboard('{Shift>}{Tab}{/Shift}')
    expect(dialog).toContainElement(document.activeElement as HTMLElement)
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(menuButton).toHaveFocus()
  })

  it('keeps the login status message in the current language after switching', async () => {
    window.history.pushState({}, '', '/dashboard')
    render(<App />)
    expect(await screen.findByText('Your session ended. Please sign in again.')).toBeInTheDocument()
    await i18n.changeLanguage('ar')
    expect(await screen.findByText('انتهت جلستك. يُرجى تسجيل الدخول مجددًا.')).toBeInTheDocument()
  })

  it('restores a saved Arabic preference when the i18n module loads', async () => {
    window.localStorage.setItem('abdullah-kit-language', 'ar')
    vi.resetModules()
    const { default: freshI18n } = await import('../lib/i18n')
    expect(freshI18n.resolvedLanguage).toBe('ar')
    expect(window.localStorage.getItem('abdullah-kit-language')).toBe('ar')
  })

  it('routes unknown paths to the bilingual not-found state', async () => {
    window.history.pushState({}, '', '/missing')
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
    await i18n.changeLanguage('ar')
    expect(await screen.findByRole('heading', { name: 'الصفحة غير موجودة' })).toBeInTheDocument()
  })

  it('redirects a protected route to sign in when no session exists', async () => {
    window.history.pushState({}, '', '/dashboard')
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/login')
  })

  it('validates login email and password before making a request', async () => {
    window.history.pushState({}, '', '/login')
    render(<App />)
    fireEvent.submit(screen.getByRole('button', { name: 'Sign in' }).closest('form')!)
    expect(await screen.findByText('Enter a valid email address.')).toBeInTheDocument()
    expect(screen.getByText('Enter your password.')).toBeInTheDocument()
  })

  it('validates registration email and minimum password length', async () => {
    window.history.pushState({}, '', '/register')
    render(<App />)
    fireEvent.submit(screen.getByRole('button', { name: 'Create account' }).closest('form')!)
    expect(await screen.findByText('Enter your full name.')).toBeInTheDocument()
    expect(screen.getByText('Enter a valid email address.')).toBeInTheDocument()
    expect(screen.getAllByText('Use at least 12 characters.').length).toBeGreaterThan(0)
  })

  it('rejects a registration password above the 128-character server limit', async () => {
    const user = userEvent.setup()
    let requests = 0
    window.history.pushState({}, '', '/register')
    authTransport.defaults.adapter = async (config) => { requests += 1; throw unauthorized(config) }
    render(<App />)
    await user.type(screen.getByLabelText('Full name'), 'Example Person')
    await user.type(screen.getByLabelText('Email address'), 'person@example.test')
    await user.click(screen.getByLabelText('Password'))
    await user.paste('x'.repeat(129))
    await user.click(screen.getByRole('button', { name: 'Create account' }))
    expect(await screen.findByText('Use 128 characters or fewer.')).toBeInTheDocument()
    expect(requests).toBe(0)
  })

  it('explains a server validation rejection instead of a generic retry message', async () => {
    const user = userEvent.setup()
    window.history.pushState({}, '', '/register')
    authTransport.defaults.adapter = async (config) => {
      const response: AxiosResponse = { data: { status: 422, detail: 'Request validation failed.' }, status: 422, statusText: 'Unprocessable Entity', headers: {}, config }
      throw new AxiosError('Unprocessable', 'ERR_BAD_REQUEST', config, undefined, response)
    }
    render(<App />)
    await user.type(screen.getByLabelText('Full name'), 'Example Person')
    await user.type(screen.getByLabelText('Email address'), 'person@example.test')
    await user.type(screen.getByLabelText('Password'), 'Example-password-123!')
    await user.click(screen.getByRole('button', { name: 'Create account' }))
    expect(await screen.findByText('Some details were not accepted. Check them and try again.')).toBeInTheDocument()
  })

  it('submits valid registration and routes to sign in', async () => {
    const user = userEvent.setup()
    window.history.pushState({}, '', '/register')
    authTransport.defaults.adapter = async (config) => ({ data: profile, status: 201, statusText: 'Created', headers: {}, config })
    render(<App />)
    await user.type(screen.getByLabelText('Full name'), 'Example Person')
    await user.type(screen.getByLabelText('Email address'), 'person@example.test')
    await user.type(screen.getByLabelText('Password'), 'Example-password-123!')
    await user.click(screen.getByRole('button', { name: 'Create account' }))
    expect(await screen.findByText('Account created. Sign in to continue.')).toBeInTheDocument()
    expect(window.location.pathname).toBe('/login')
  })

  it('submits valid login and opens the guarded dashboard', async () => {
    const user = userEvent.setup()
    let authenticated = false
    window.history.pushState({}, '', '/login')
    api.defaults.adapter = async (config) => {
      if (!authenticated) throw unauthorized(config)
      return { data: profile, status: 200, statusText: 'OK', headers: {}, config }
    }
    authTransport.defaults.adapter = async (config) => {
      if (config.url === '/auth/login') authenticated = true
      return { data: profile, status: 200, statusText: 'OK', headers: {}, config }
    }
    render(<App />)
    await user.type(screen.getByLabelText('Email address'), 'person@example.test')
    await user.type(screen.getByLabelText('Password'), 'Example-password-123!')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByRole('heading', { name: 'Welcome back, Example Person.' })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/dashboard')
  })
})
