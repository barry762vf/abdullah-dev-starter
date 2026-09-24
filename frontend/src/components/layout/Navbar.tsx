import { LogIn, LogOut, Menu } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useState } from 'react'
import { ApiError, logout } from '../../lib/api'
import { useCurrentUser } from '../../features/auth/useCurrentUser'
import { useUiStore } from '../../stores/uiStore'
import { LanguageToggle } from './LanguageToggle'
import { ThemeToggle } from './ThemeToggle'

export function Navbar() {
  const { t } = useTranslation()
  const user = useCurrentUser().data
  const menuOpen = useUiStore((state) => state.menuOpen)
  const setMenuOpen = useUiStore((state) => state.setMenuOpen)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(false)

  async function signOut() {
    setBusy(true)
    setError(false)
    try {
      await logout()
    } catch (failure) {
      if (failure instanceof ApiError) setError(true)
    } finally {
      setBusy(false)
    }
  }

  return (
    <header className="relative flex min-h-20 items-center justify-between gap-3 border-b border-slate-200/80 bg-white/90 px-4 backdrop-blur md:px-8 dark:border-slate-800 dark:bg-slate-900/90">
      <div className="flex min-w-0 items-center gap-3">
        <button type="button" className="icon-button md:hidden" onClick={() => setMenuOpen(true)} aria-label={t('common.openMenu')} aria-expanded={menuOpen} aria-controls="mobile-navigation">
          <Menu size={20} aria-hidden="true" />
        </button>
        <span className="flex size-8 items-center justify-center rounded-xl bg-accent text-sm font-extrabold text-white sm:hidden" aria-hidden="true">A</span>
        <div className="hidden min-w-0 sm:block">
          <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-muted dark:text-slate-400">{t('nav.foundation')}</p>
          <p className="truncate text-sm font-semibold text-ink dark:text-white">{t('nav.workspace')}</p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <LanguageToggle />
        <ThemeToggle />
        <span className="mx-1 hidden h-7 w-px bg-slate-200 sm:block dark:bg-slate-700" aria-hidden="true" />
        {user ? (
          <button type="button" className="icon-button gap-2 px-3" onClick={() => void signOut()} disabled={busy} aria-label={t('common.signOut')} title={t('common.signOut')}>
            <LogOut size={17} className="rtl:-scale-x-100" aria-hidden="true" />
            <span className="hidden text-sm font-semibold sm:inline">{t('common.signOut')}</span>
          </button>
        ) : (
          <Link to="/login" className="button-primary min-w-10 px-3 py-2 text-sm sm:px-5" aria-label={t('common.signIn')}>
            <LogIn size={18} className="sm:hidden rtl:-scale-x-100" aria-hidden="true" />
            <span className="hidden whitespace-nowrap sm:inline">{t('common.signIn')}</span>
          </Link>
        )}
      </div>
      {error && <p role="alert" className="absolute end-4 top-full mt-2 rounded-lg bg-red-50 p-2 text-xs text-red-700 shadow-panel dark:bg-red-500/10 dark:text-red-300">{t('auth.signOutFailed')}</p>}
    </header>
  )
}
