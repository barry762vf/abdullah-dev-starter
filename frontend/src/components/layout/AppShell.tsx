import { Outlet } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Navbar } from './Navbar'
import { Sidebar } from './Sidebar'

export function AppShell() {
  const { t } = useTranslation()
  return (
    <div className="min-h-screen bg-surface text-ink md:grid md:grid-cols-[16rem_minmax(0,1fr)] dark:bg-slate-950 dark:text-slate-100">
      <a href="#main-content" className="skip-link">{t('common.skipToContent')}</a>
      <Sidebar />
      <div className="min-w-0">
        <Navbar />
        <main id="main-content" className="mx-auto w-full max-w-6xl px-5 py-8 sm:px-8 md:py-11 lg:px-12">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
