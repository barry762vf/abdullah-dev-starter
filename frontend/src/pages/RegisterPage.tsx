import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { AuthPageFrame } from '../components/layout/AuthPageFrame'
import { ApiError, register } from '../lib/api'

export function RegisterPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<{ fullName?: string; email?: string; password?: string }>({})
  const [serverError, setServerError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const nextErrors = {
      fullName: fullName.trim() ? undefined : t('auth.nameRequired'),
      email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim()) ? undefined : t('auth.invalidEmail'),
      password: password.length < 12 ? t('auth.passwordTooShort') : password.length > 128 ? t('auth.passwordTooLong') : undefined,
    }
    setErrors(nextErrors)
    if (nextErrors.fullName || nextErrors.email || nextErrors.password) return
    setBusy(true)
    setServerError('')
    try {
      await register({ full_name: fullName.trim(), email: email.trim(), password })
      navigate('/login', { replace: true, state: { messageKey: 'auth.registerSuccess' } })
    } catch (error) {
      setServerError(error instanceof ApiError && error.status === 409 ? t('auth.emailTaken') : error instanceof ApiError && error.status === 429 ? t('auth.rateLimited') : error instanceof ApiError && error.status === 503 ? t('auth.registerUnavailable') : error instanceof ApiError && error.status === 422 ? t('auth.invalidDetails') : t('states.errorBody'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthPageFrame eyebrow={t('nav.workspace')} title={t('auth.registerTitle')} description={t('auth.registerDescription')}>
      <form onSubmit={(event) => void submit(event)} noValidate className="space-y-5">
        <div>
          <label className="form-label" htmlFor="register-name">{t('common.fullName')}</label>
          <input className="form-input" id="register-name" type="text" autoComplete="name" value={fullName} onChange={(event) => setFullName(event.target.value)} aria-invalid={Boolean(errors.fullName)} aria-describedby={errors.fullName ? 'register-name-error' : undefined} required />
          {errors.fullName && <p id="register-name-error" className="mt-2 text-sm text-red-600" role="alert">{errors.fullName}</p>}
        </div>
        <div>
          <label className="form-label" htmlFor="register-email">{t('common.email')}</label>
          <input className="form-input" id="register-email" type="email" dir="ltr" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} aria-invalid={Boolean(errors.email)} aria-describedby={errors.email ? 'register-email-error' : undefined} required />
          {errors.email && <p id="register-email-error" className="mt-2 text-sm text-red-600" role="alert">{errors.email}</p>}
        </div>
        <div>
          <label className="form-label" htmlFor="register-password">{t('common.password')}</label>
          <input className="form-input" id="register-password" type="password" dir="ltr" autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} aria-invalid={Boolean(errors.password)} aria-describedby={errors.password ? 'register-password-error' : 'register-password-hint'} minLength={12} required />
          <p id="register-password-hint" className="mt-2 text-xs text-muted dark:text-slate-300">{t('auth.passwordHint')}</p>
          {errors.password && <p id="register-password-error" className="mt-2 text-sm text-red-600" role="alert">{errors.password}</p>}
        </div>
        {serverError && <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">{serverError}</p>}
        <button type="submit" className="button-primary w-full" disabled={busy}>{busy ? t('common.loading') : t('common.createAccount')}</button>
      </form>
      <p className="mt-7 text-center text-sm text-muted dark:text-slate-300">{t('auth.haveAccount')} <Link to="/login" className="font-bold text-accent hover:underline dark:text-blue-300">{t('common.signIn')}</Link></p>
    </AuthPageFrame>
  )
}
