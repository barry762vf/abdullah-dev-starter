import type { TFunction } from 'i18next'

/** Seeded roles are translated; project-specific role names are shown as stored (plain text). */
export function roleLabel(t: TFunction, role: string): string {
  return t(`admin.roles.${role}`, { defaultValue: role })
}

export function formatDateTime(value: string, language: string | undefined): string {
  return new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}
