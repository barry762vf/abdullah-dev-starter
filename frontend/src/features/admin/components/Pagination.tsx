import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useTranslation } from 'react-i18next'

type Props = { page: number; pageSize: number; total: number; onPage: (page: number) => void; label: string }

export function Pagination({ page, pageSize, total, onPage, label }: Props) {
  const { t } = useTranslation()
  const pages = Math.max(1, Math.ceil(total / pageSize))

  return (
    <nav aria-label={label} className="flex flex-wrap items-center justify-between gap-3 text-sm">
      <p className="text-muted dark:text-slate-300" aria-live="polite">{t('admin.pagination.status', { page, pages, total })}</p>
      <div className="flex gap-2">
        <button type="button" className="button-secondary min-h-10 gap-1 px-3" disabled={page <= 1} onClick={() => onPage(page - 1)}>
          {/* Chevrons point toward the inline start/end, so they mirror in RTL. */}
          <ChevronLeft size={16} className="rtl:-scale-x-100" aria-hidden="true" />
          {t('admin.pagination.previous')}
        </button>
        <button type="button" className="button-secondary min-h-10 gap-1 px-3" disabled={page >= pages} onClick={() => onPage(page + 1)}>
          {t('admin.pagination.next')}
          <ChevronRight size={16} className="rtl:-scale-x-100" aria-hidden="true" />
        </button>
      </div>
    </nav>
  )
}
