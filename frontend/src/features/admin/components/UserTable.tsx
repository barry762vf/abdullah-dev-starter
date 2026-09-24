import { useState } from 'react'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Dialog } from '../../../components/feedback/Dialog'
import { StatePanel } from '../../../components/feedback/StatePanel'
import { useDebouncedValue } from '../../../hooks/useDebouncedValue'
import { ApiError } from '../../../lib/api'
import type { User } from '../../../types/auth'
import { useCurrentUser } from '../../auth/useCurrentUser'
import { adminKeys, fetchUsers, PAGE_SIZE, updateUser, type UserUpdate } from '../api'
import { ASSIGNABLE_ROLES, canManage, isSuperadmin, primaryRole } from '../roles'
import { formatDateTime, roleLabel } from './labels'
import { Pagination } from './Pagination'

type Pending = { user: User; changes: UserUpdate; kind: 'disable' | 'role' }

function mutationError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 403) return 'admin.errors.forbidden'
    if (error.status === 404) return 'admin.errors.notFound'
    if (error.status === 409) return 'admin.errors.lastSuperadmin'
  }
  return 'admin.errors.generic'
}

export function UserTable() {
  const { t, i18n } = useTranslation()
  const queryClient = useQueryClient()
  const actor = useCurrentUser().data
  const [search, setSearch] = useState('')
  const [role, setRole] = useState('')
  const [page, setPage] = useState(1)
  const [pending, setPending] = useState<Pending | null>(null)
  const term = useDebouncedValue(search.trim())

  const users = useQuery({
    queryKey: adminKeys.users(page, term, role),
    queryFn: ({ signal }) => fetchUsers(page, term, role, signal),
    placeholderData: keepPreviousData,
  })
  const mutation = useMutation({
    mutationFn: ({ user, changes }: Pending | { user: User; changes: UserUpdate }) => updateUser(user.id, changes),
    onSuccess: () => {
      setPending(null)
      void queryClient.invalidateQueries({ queryKey: adminKeys.all })
    },
  })

  function run(action: Pending | { user: User; changes: UserUpdate }) {
    mutation.reset()
    mutation.mutate(action)
  }

  const statusBadge = (active: boolean) => (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-bold ${active ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300' : 'bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-300'}`}>
      {active ? t('admin.users.active') : t('admin.users.disabled')}
    </span>
  )

  return (
    <section className="space-y-5" aria-labelledby="users-heading">
      <h2 id="users-heading" className="text-xl font-bold">{t('admin.users.title')}</h2>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="flex-1">
          <label className="form-label" htmlFor="admin-user-search">{t('admin.users.search')}</label>
          <input
            id="admin-user-search"
            className="form-input"
            type="search"
            value={search}
            maxLength={100}
            placeholder={t('admin.users.searchPlaceholder')}
            onChange={(event) => { setSearch(event.target.value); setPage(1) }}
          />
        </div>
        <div className="sm:w-56">
          <label className="form-label" htmlFor="admin-role-filter">{t('admin.users.roleFilter')}</label>
          <select id="admin-role-filter" className="form-input" value={role} onChange={(event) => { setRole(event.target.value); setPage(1) }}>
            <option value="">{t('admin.users.allRoles')}</option>
            {ASSIGNABLE_ROLES.map((name) => <option key={name} value={name}>{roleLabel(t, name)}</option>)}
          </select>
        </div>
      </div>

      {mutation.isError && !pending && (
        <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">{t(mutationError(mutation.error))}</p>
      )}

      {users.isPending ? (
        <StatePanel kind="loading" />
      ) : users.isError ? (
        <StatePanel kind="error" onRetry={() => void users.refetch()} />
      ) : users.data.items.length === 0 ? (
        <StatePanel kind="empty" title={t('admin.users.emptyTitle')} body={t('admin.users.emptyBody')} />
      ) : (
        <>
          {/* Focusable scroll region; `relative` also contains the table's sr-only labels so they cannot widen the page. */}
          <div className="panel relative overflow-x-auto" role="region" aria-labelledby="users-heading" tabIndex={0}>
            <table className="w-full min-w-[46rem] text-start text-sm">
              <thead className="border-b border-slate-200 text-xs uppercase tracking-wider text-muted dark:border-slate-800 dark:text-slate-400">
                <tr>
                  <th scope="col" className="px-4 py-3 text-start font-bold">{t('admin.users.user')}</th>
                  <th scope="col" className="px-4 py-3 text-start font-bold">{t('admin.users.roles')}</th>
                  <th scope="col" className="px-4 py-3 text-start font-bold">{t('admin.users.status')}</th>
                  <th scope="col" className="px-4 py-3 text-start font-bold">{t('admin.users.joined')}</th>
                  <th scope="col" className="px-4 py-3 text-start font-bold">{t('admin.users.actions')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {users.data.items.map((user) => {
                  const manageable = canManage(actor, user)
                  const busy = mutation.isPending && mutation.variables?.user.id === user.id
                  return (
                    <tr key={user.id}>
                      <td className="px-4 py-3">
                        <p className="font-semibold text-ink dark:text-white">{user.full_name}{user.id === actor?.id && <span className="ms-2 text-xs font-bold text-accent dark:text-blue-300">({t('admin.users.you')})</span>}</p>
                        <p className="break-all text-muted dark:text-slate-400" dir="ltr">{user.email}</p>
                      </td>
                      <td className="px-4 py-3">
                        <ul className="flex flex-wrap gap-1.5">
                          {user.roles.map((name) => (
                            <li key={name} className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-semibold dark:bg-slate-800">{roleLabel(t, name)}</li>
                          ))}
                        </ul>
                      </td>
                      <td className="px-4 py-3">{statusBadge(user.is_active)}</td>
                      <td className="whitespace-nowrap px-4 py-3 text-muted dark:text-slate-400">{formatDateTime(user.created_at, i18n.resolvedLanguage)}</td>
                      <td className="px-4 py-3">
                        {manageable ? (
                          <div className="flex flex-wrap items-center gap-2">
                            {isSuperadmin(actor) && (
                              <>
                                <label className="sr-only" htmlFor={`role-${user.id}`}>{t('admin.users.roleFor', { name: user.full_name })}</label>
                                <select
                                  id={`role-${user.id}`}
                                  className="form-input min-h-10 w-auto py-1"
                                  value={primaryRole(user)}
                                  disabled={busy}
                                  onChange={(event) => setPending({ user, changes: { roles: [event.target.value] }, kind: 'role' })}
                                >
                                  {ASSIGNABLE_ROLES.map((name) => <option key={name} value={name}>{roleLabel(t, name)}</option>)}
                                </select>
                              </>
                            )}
                            <button
                              type="button"
                              className="button-secondary min-h-10 px-3 text-xs"
                              disabled={busy}
                              aria-label={t(user.is_active ? 'admin.users.disableFor' : 'admin.users.enableFor', { name: user.full_name })}
                              onClick={() => (user.is_active
                                ? setPending({ user, changes: { is_active: false }, kind: 'disable' })
                                : run({ user, changes: { is_active: true } }))}
                            >
                              {user.is_active ? t('admin.users.disable') : t('admin.users.enable')}
                            </button>
                          </div>
                        ) : (
                          <span className="text-xs text-muted dark:text-slate-400">{t('admin.users.noActions')}</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <Pagination page={page} pageSize={PAGE_SIZE} total={users.data.total} onPage={setPage} label={t('admin.pagination.users')} />
        </>
      )}

      {pending && (
        <Dialog
          title={t(pending.kind === 'disable' ? 'admin.confirm.disableTitle' : 'admin.confirm.roleTitle')}
          onClose={() => { setPending(null); mutation.reset() }}
          actions={
            <>
              <button type="button" className="button-secondary" onClick={() => { setPending(null); mutation.reset() }}>{t('common.cancel')}</button>
              <button type="button" className="button-primary" disabled={mutation.isPending} onClick={() => run(pending)}>
                {t(pending.kind === 'disable' ? 'admin.users.disable' : 'admin.confirm.changeRole')}
              </button>
            </>
          }
        >
          <p>
            {pending.kind === 'disable'
              ? t('admin.confirm.disableBody', { name: pending.user.full_name })
              : t('admin.confirm.roleBody', { name: pending.user.full_name, from: roleLabel(t, primaryRole(pending.user)), to: roleLabel(t, pending.changes.roles?.[0] ?? '') })}
          </p>
          {mutation.isError && <p role="alert" className="mt-3 font-semibold text-red-700 dark:text-red-300">{t(mutationError(mutation.error))}</p>}
        </Dialog>
      )}
    </section>
  )
}
