import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { StatePanel } from '../../../components/feedback/StatePanel'
import { adminKeys, fetchStats } from '../api'
import { roleLabel } from './labels'

export function AdminOverview() {
  const { t, i18n } = useTranslation()
  const { data, isPending, error, refetch } = useQuery({ queryKey: adminKeys.stats, queryFn: ({ signal }) => fetchStats(signal) })

  if (isPending) return <StatePanel kind="loading" />
  if (error || !data) return <StatePanel kind="error" onRetry={() => void refetch()} />

  const number = new Intl.NumberFormat(i18n.resolvedLanguage)
  const cards = [
    { key: 'usersTotal', value: data.users_total },
    { key: 'usersActive', value: data.users_active },
    { key: 'usersDisabled', value: data.users_disabled },
    { key: 'usersVerified', value: data.users_verified },
    { key: 'activeSessions', value: data.active_sessions },
  ]

  return (
    <div className="space-y-6">
      <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map(({ key, value }) => (
          <div key={key} className="panel p-5">
            <dt className="text-sm font-semibold text-muted dark:text-slate-300">{t(`admin.stats.${key}`)}</dt>
            <dd className="mt-2 text-3xl font-extrabold tabular-nums">{number.format(value)}</dd>
            <dd className="mt-1 text-xs leading-5 text-muted dark:text-slate-400">{t(`admin.stats.${key}Hint`)}</dd>
          </div>
        ))}
      </dl>
      <section className="panel p-5" aria-labelledby="role-counts-heading">
        <h2 id="role-counts-heading" className="text-lg font-bold">{t('admin.stats.rolesTitle')}</h2>
        <ul className="mt-4 divide-y divide-slate-100 dark:divide-slate-800">
          {data.roles.map((role) => (
            <li key={role.name} className="flex items-center justify-between py-2.5 text-sm">
              <span>{roleLabel(t, role.name)}</span>
              <span className="font-bold tabular-nums">{number.format(role.users)}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
