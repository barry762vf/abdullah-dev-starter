import { useState, type FormEvent } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { AuthPageFrame } from '../components/layout/AuthPageFrame'
import { currentUserKey } from '../features/auth/useCurrentUser'
import { ApiError, login } from '../lib/api'

// Status messages travel as translation keys so they follow a later language switch.
const MESSAGE_KEYS = new Set(['auth.sessionExpired', 'auth.registerSuccess'])

// Exact allowlist of protected routes; anything else falls back to the dashboard (no open redirect).
const DESTINATIONS = new Set(['/dashboard', '/admin', '/admin/users', '/admin/audit-logs'])

function destination(value: unknown): string {
  return typeof value === 'string' && DESTINATIONS.has(value) ? value : '/dashboard'
}

export function LoginPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const state = location.state as { from?: unknown; messageKey?: unknown } | null
  const messageKey = typeof state?.messageKey === 'string' && MESSAGE_KEYS.has(state.messageKey) ? state.messageKey : null
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({})
  const [serverError, setServerError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const nextErrors = {
      email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim()) ? undefined : t('auth.invalidEmail'),
      password: password ? undefined : t('auth.passwordRequired'),
    }
    setErrors(nextErrors)
    if (nextErrors.email || nextErrors.password) return
    setBusy(true)
    setServerError('')
    try {
      const user = await login({ email: email.trim(), password })
      queryClient.setQueryData(currentUserKey, user)
      navigate(destination(state?.from), { replace: true })
    } catch (error) {
      setServerError(error instanceof ApiError && error.status === 401 ? t('auth.invalidCredentials') : error instanceof ApiError && error.status === 429 ? t('auth.rateLimited') : t('states.errorBody'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthPageFrame eyebrow={t('nav.workspace')} title={t('auth.loginTitle')} description={t('auth.loginDescription')}>
      {messageKey && <p role="status" className="mb-5 rounded-xl bg-blue-50 p-3 text-sm text-blue-800 dark:bg-blue-500/10 dark:text-blue-200">{t(messageKey)}</p>}
      <form onSubmit={(event) => void submit(event)} noValidate className="space-y-5">
        <div>
          <label className="form-label" htmlFor="login-email">{t('common.email')}</label>
          <input className="form-input" id="login-email" type="email" dir="ltr" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} aria-invalid={Boolean(errors.email)} aria-describedby={errors.email ? 'login-email-error' : undefined} required />
          {errors.email && <p id="login-email-error" className="mt-2 text-sm text-red-600" role="alert">{errors.email}</p>}
        </div>
        <div>
          <label className="form-label" htmlFor="login-password">{t('common.password')}</label>
          <input className="form-input" id="login-password" type="password" dir="ltr" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} aria-invalid={Boolean(errors.password)} aria-describedby={errors.password ? 'login-password-error' : undefined} required />
          {errors.password && <p id="login-password-error" className="mt-2 text-sm text-red-600" role="alert">{errors.password}</p>}
        </div>
        {serverError && <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">{serverError}</p>}
        <button type="submit" className="button-primary w-full" disabled={busy}>{busy ? t('common.loading') : t('common.signIn')}</button>
      </form>
      <p className="mt-7 text-center text-sm text-muted dark:text-slate-300">{t('auth.noAccount')} <Link to="/register" className="font-bold text-accent hover:underline dark:text-blue-300">{t('common.createAccount')}</Link></p>
    </AuthPageFrame>
  )
}
