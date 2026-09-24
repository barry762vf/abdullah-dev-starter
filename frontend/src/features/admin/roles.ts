import type { User } from '../../types/auth'

export const ADMIN_ROLES = ['admin'] as const
export const ASSIGNABLE_ROLES = ['user', 'admin', 'superadmin'] as const
const MANAGEMENT_ROLES = new Set(['admin', 'superadmin'])

/**
 * Mirrors the backend guard for UX only: superadmin satisfies every role check.
 * The server re-checks current database roles on every admin request.
 */
export function hasRole(user: User | null | undefined, allowed: readonly string[]): boolean {
  if (!user) return false
  return user.roles.includes('superadmin') || user.roles.some((role) => allowed.includes(role))
}

export function isSuperadmin(user: User | null | undefined): boolean {
  return Boolean(user?.roles.includes('superadmin'))
}

/** Same rule as ADR 013: never yourself; only a superadmin manages administrator accounts. */
export function canManage(actor: User | null | undefined, target: User): boolean {
  if (!actor || actor.id === target.id || !hasRole(actor, ADMIN_ROLES)) return false
  return isSuperadmin(actor) || !target.roles.some((role) => MANAGEMENT_ROLES.has(role))
}

/** The highest seeded role, used as the value of the single role selector. */
export function primaryRole(user: User): string {
  return ASSIGNABLE_ROLES.slice().reverse().find((role) => user.roles.includes(role)) ?? user.roles[0] ?? 'user'
}
