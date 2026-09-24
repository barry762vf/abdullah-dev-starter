import { useTranslation } from 'react-i18next'
import { StatePanel } from '../components/feedback/StatePanel'
import { useCurrentUser } from '../features/auth/useCurrentUser'

export function DashboardPage() {
  const { t } = useTranslation()
  const user = useCurrentUser().data

  return (
    <div className="space-y-7">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-accent dark:text-blue-300">{t('dashboard.eyebrow')}</p>
        <h1 className="mt-3 text-3xl font-extrabold tracking-tight sm:text-4xl">{t('dashboard.title', { name: user?.full_name ?? '' })}</h1>
        <p className="mt-3 text-muted dark:text-slate-300">{t('dashboard.description')}</p>
      </div>
      <StatePanel kind="empty" />
    </div>
  )
}
