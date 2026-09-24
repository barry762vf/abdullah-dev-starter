import { apiRequest } from '../../lib/api'
import type { User } from '../../types/auth'

export type Page<T> = { items: T[]; total: number; page: number; page_size: number }

export type AdminStats = {
  users_total: number
  users_active: number
  users_disabled: number
  users_verified: number
  roles: { name: string; users: number }[]
  active_sessions: number
  generated_at: string
}

export type AuditLogEntry = {
  id: string
  created_at: string
  action: string
  entity: string
  entity_id: string | null
  actor: { id: string; email: string } | null
  ip_address: string | null
  user_agent: string | null
  details: Record<string, unknown>
}

export type UserUpdate = { is_active?: boolean; is_verified?: boolean; roles?: string[] }

export const PAGE_SIZE = 20

export const adminKeys = {
  all: ['admin'] as const,
  stats: ['admin', 'stats'] as const,
  users: (page: number, search: string, role: string) => ['admin', 'users', { page, search, role }] as const,
  audit: (page: number, action: string) => ['admin', 'audit', { page, action }] as const,
}

// Empty filters are omitted so the backend receives only meaningful parameters.
function params(values: Record<string, string | number>) {
  return Object.fromEntries(Object.entries(values).filter(([, value]) => value !== ''))
}

export function fetchStats(signal?: AbortSignal) {
  return apiRequest<AdminStats>({ url: '/admin/stats', signal })
}

export function fetchUsers(page: number, search: string, role: string, signal?: AbortSignal) {
  return apiRequest<Page<User>>({ url: '/admin/users', params: params({ page, page_size: PAGE_SIZE, search, role }), signal })
}

export function fetchAuditLogs(page: number, action: string, signal?: AbortSignal) {
  return apiRequest<Page<AuditLogEntry>>({ url: '/admin/audit-logs', params: params({ page, page_size: PAGE_SIZE, action }), signal })
}

export function updateUser(id: string, changes: UserUpdate) {
  return apiRequest<User>({ url: `/admin/users/${encodeURIComponent(id)}`, method: 'PATCH', data: changes })
}
