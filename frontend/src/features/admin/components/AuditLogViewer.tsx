import { useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Dialog } from '../../../components/feedback/Dialog'
import { StatePanel } from '../../../components/feedback/StatePanel'
import { adminKeys, fetchAuditLogs, PAGE_SIZE, type AuditLogEntry } from '../api'
import { formatDateTime } from './labels'
import { Pagination } from './Pagination'

// Actions written by the backend today (auth_service, seed, admin_service).
const ACTIONS = [
  'admin.user_update',
  'auth.login',
  'auth.login_failed',
  'auth.login_throttled',
  'auth.register',
  'auth.refresh',
  'auth.refresh_reuse',
  'auth.logout',
  'auth.bootstrap',
] as const

/**
 * Audit data includes attacker-controlled values (user agent, IP, identifiers). Everything here is
 * rendered as React text nodes, which escape markup; never switch these to HTML rendering.
 */
export function AuditLogViewer() {
  const { t, i18n } = useTranslation()
  const [action, setAction] = useState('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<AuditLogEntry | null>(null)
  const logs = useQuery({
    queryKey: adminKeys.audit(page, action),
    queryFn: ({ signal }) => fetchAuditLogs(page, action, signal),
    placeholderData: keepPreviousData,
  })

  return (
    <section className="space-y-5" aria-labelledby="audit-heading">
      <h2 id="audit-heading" className="text-xl font-bold">{t('admin.audit.title')}</h2>
      <div className="sm:w-72">
        <label className="form-label" htmlFor="audit-action-filter">{t('admin.audit.actionFilter')}</label>
        <select id="audit-action-filter" className="form-input" dir="ltr" value={action} onChange={(event) => { setAction(event.target.value); setPage(1) }}>
          <option value="">{t('admin.audit.allActions')}</option>
          {ACTIONS.map((name) => <option key={name} value={name}>{name}</option>)}
        </select>
      </div>

      {logs.isPending ? (
        <StatePanel kind="loading" />
      ) : logs.isError ? (
        <StatePanel kind="error" onRetry={() => void logs.refetch()} />
      ) : logs.data.items.length === 0 ? (
        <StatePanel kind="empty" title={t('admin.audit.emptyTitle')} body={t('admin.audit.emptyBody')} />
      ) : (
        <>
          <div className="panel relative overflow-x-auto" role="region" aria-labelledby="audit-heading" tabIndex={0}>
            <table className="w-full min-w-[44rem] text-sm">
              <thead className="border-b border-slate-200 text-xs uppercase tracking-wider text-muted dark:border-slate-800 dark:text-slate-400">
                <tr>
                  <th scope="col" className="px-4 py-3 text-start font-bold">{t('admin.audit.time')}</th>
                  <th scope="col" className="px-4 py-3 text-start font-bold">{t('admin.audit.action')}</th>
                  <th scope="col" className="px-4 py-3 text-start font-bold">{t('admin.audit.actor')}</th>
                  <th scope="col" className="px-4 py-3 text-start font-bold">{t('admin.audit.ip')}</th>
                  <th scope="col" className="px-4 py-3 text-start font-bold">{t('admin.audit.userAgent')}</th>
                  <th scope="col" className="px-4 py-3 text-start font-bold"><span className="sr-only">{t('admin.audit.details')}</span></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {logs.data.items.map((entry) => (
                  <tr key={entry.id}>
                    <td className="whitespace-nowrap px-4 py-3 text-muted dark:text-slate-400">{formatDateTime(entry.created_at, i18n.resolvedLanguage)}</td>
                    <td className="px-4 py-3 font-mono text-xs" dir="ltr">{entry.action}</td>
                    <td className="max-w-[14rem] break-all px-4 py-3" dir="ltr">{entry.actor?.email ?? t('admin.audit.system')}</td>
                    <td className="px-4 py-3 font-mono text-xs" dir="ltr">{entry.ip_address ?? '—'}</td>
                    <td className="max-w-[16rem] px-4 py-3 text-muted dark:text-slate-400">
                      <span className="line-clamp-2 break-all" dir="ltr">{entry.user_agent ?? '—'}</span>
                    </td>
                    <td className="px-4 py-3">
                      <button type="button" className="button-secondary min-h-10 px-3 text-xs" onClick={() => setSelected(entry)} aria-label={t('admin.audit.detailsFor', { action: entry.action })}>
                        {t('admin.audit.details')}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={page} pageSize={PAGE_SIZE} total={logs.data.total} onPage={setPage} label={t('admin.pagination.audit')} />
        </>
      )}

      {selected && (
        <Dialog title={t('admin.audit.detailsTitle')} onClose={() => setSelected(null)}>
          <dl className="grid gap-3">
            {[
              ['admin.audit.time', formatDateTime(selected.created_at, i18n.resolvedLanguage)],
              ['admin.audit.action', selected.action],
              ['admin.audit.actor', selected.actor?.email ?? t('admin.audit.system')],
              ['admin.audit.target', [selected.entity, selected.entity_id].filter(Boolean).join(' ')],
              ['admin.audit.ip', selected.ip_address ?? '—'],
              ['admin.audit.userAgent', selected.user_agent ?? '—'],
            ].map(([key, value]) => (
              <div key={key}>
                <dt className="text-xs font-bold uppercase tracking-wider">{t(key)}</dt>
                <dd className="break-all text-ink dark:text-slate-100" dir="ltr">{value}</dd>
              </div>
            ))}
            <div>
              <dt className="text-xs font-bold uppercase tracking-wider">{t('admin.audit.details')}</dt>
              <dd>
                <pre className="mt-1 max-h-64 overflow-auto whitespace-pre-wrap break-all rounded-lg bg-slate-100 p-3 text-xs text-ink dark:bg-slate-800 dark:text-slate-100" dir="ltr">
                  {JSON.stringify(selected.details, null, 2)}
                </pre>
              </dd>
            </div>
          </dl>
        </Dialog>
      )}
    </section>
  )
}
