import { House, LayoutDashboard, ShieldCheck, X } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ADMIN_ROLES, hasRole } from '../../features/admin/roles'
import { useCurrentUser } from '../../features/auth/useCurrentUser'
import { useDialogFocus } from '../../hooks/useDialogFocus'
import { useUiStore } from '../../stores/uiStore'

const links = [
  { to: '/', key: 'nav.home', icon: House, end: true },
  { to: '/dashboard', key: 'nav.dashboard', icon: LayoutDashboard, end: false },
]
// Shown only to administrators for convenience; the admin API itself enforces access.
const adminLink = { to: '/admin', key: 'nav.admin', icon: ShieldCheck, end: false }

function SidebarContent({ close }: { close: () => void }) {
  const { t } = useTranslation()
  const user = useCurrentUser().data
  const visible = hasRole(user, ADMIN_ROLES) ? [...links, adminLink] : links
  return (
    <>
      <div className="flex h-20 items-center justify-between border-b border-slate-200/70 px-6 dark:border-slate-700">
        <NavLink to="/" onClick={close} className="flex items-center gap-3 text-ink dark:text-white">
          <span className="flex size-10 items-center justify-center rounded-2xl bg-accent text-xl font-extrabold text-white shadow-lg shadow-blue-500/20" aria-hidden="true">A</span>
          <span className="text-[15px] font-bold tracking-tight">{t('common.appName')}</span>
        </NavLink>
        <button className="icon-button md:hidden" type="button" onClick={close} aria-label={t('common.closeMenu')}>
          <X size={18} aria-hidden="true" />
        </button>
      </div>
      <nav aria-label={t('nav.workspace')} className="flex-1 px-4 py-7">
        <p className="px-3 text-[11px] font-bold uppercase tracking-[0.17em] text-muted dark:text-slate-400">{t('nav.workspace')}</p>
        <div className="mt-4 space-y-1.5">
          {visible.map(({ to, key, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={close}
              className={({ isActive }) => `flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm font-semibold transition-colors ${isActive ? 'bg-blue-50 text-accent dark:bg-blue-500/15 dark:text-blue-300' : 'text-muted hover:bg-slate-100 hover:text-ink dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white'}`}
            >
              <Icon size={18} strokeWidth={2} aria-hidden="true" />
              {t(key)}
            </NavLink>
          ))}
        </div>
      </nav>
      <div className="mx-4 mb-5 rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800/60">
        <p className="text-xs font-bold uppercase tracking-widest text-accent dark:text-blue-300">{t('nav.foundation')}</p>
        <p className="mt-2 text-sm leading-relaxed text-muted dark:text-slate-300">{t('home.foundationValue')}</p>
      </div>
    </>
  )
}

function MobileDrawer({ close }: { close: () => void }) {
  const { t } = useTranslation()
  const { ref: panel, onKeyDown } = useDialogFocus<HTMLElement>(close)

  return (
    <div className="fixed inset-0 z-40 md:hidden">
      <div className="absolute inset-0 bg-ink/45" aria-hidden="true" onClick={close} />
      <aside
        id="mobile-navigation"
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-label={t('nav.workspace')}
        onKeyDown={onKeyDown}
        className="absolute inset-y-0 start-0 flex w-[min(82vw,19rem)] flex-col bg-white shadow-panel dark:bg-slate-900"
      >
        <SidebarContent close={close} />
      </aside>
    </div>
  )
}

export function Sidebar() {
  const open = useUiStore((state) => state.menuOpen)
  const close = () => useUiStore.getState().setMenuOpen(false)

  return (
    <>
      <aside className="hidden min-h-screen flex-col border-e border-slate-200 bg-white md:flex dark:border-slate-800 dark:bg-slate-900">
        <SidebarContent close={close} />
      </aside>
      {open && <MobileDrawer close={close} />}
    </>
  )
}
