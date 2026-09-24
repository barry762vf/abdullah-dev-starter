import { NavLink, Outlet } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

const sections = [
  { to: '/admin', key: 'admin.nav.overview', end: true },
  { to: '/admin/users', key: 'admin.nav.users', end: false },
  { to: '/admin/audit-logs', key: 'admin.nav.audit', end: false },
] as const

/** Administration layout: page heading, section navigation, and the active section. */
export function AdminPage() {
  const { t } = useTranslation()

  return (
    <div className="space-y-7">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-accent dark:text-blue-300">{t('admin.eyebrow')}</p>
        <h1 className="mt-3 text-3xl font-extrabold tracking-tight sm:text-4xl">{t('admin.title')}</h1>
        <p className="mt-3 text-muted dark:text-slate-300">{t('admin.description')}</p>
      </div>
      <nav aria-label={t('admin.nav.label')} className="flex gap-2 overflow-x-auto overflow-y-hidden border-b border-slate-200 dark:border-slate-800">
        {sections.map(({ to, key, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) => `whitespace-nowrap border-b-2 px-3 py-3 text-sm font-semibold transition-colors ${isActive ? 'border-accent text-accent dark:text-blue-300' : 'border-transparent text-muted hover:text-ink dark:text-slate-300 dark:hover:text-white'}`}
          >
            {t(key)}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  )
}
