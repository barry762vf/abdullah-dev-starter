import { useId, type ReactNode } from 'react'
import { X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useDialogFocus } from '../../hooks/useDialogFocus'

type Props = { title: string; onClose: () => void; children: ReactNode; actions?: ReactNode }

/** Accessible modal: labelled dialog, focus kept inside, Escape and backdrop close it. */
export function Dialog({ title, onClose, children, actions }: Props) {
  const { t } = useTranslation()
  const titleId = useId()
  const { ref, onKeyDown } = useDialogFocus<HTMLDivElement>(onClose)

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center p-4 sm:items-center">
      <div className="absolute inset-0 bg-ink/45" aria-hidden="true" onClick={onClose} />
      <div
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onKeyDown={onKeyDown}
        className="panel relative flex max-h-[85vh] w-full max-w-lg flex-col p-6"
      >
        <div className="flex items-start justify-between gap-4">
          <h2 id={titleId} className="text-lg font-bold">{title}</h2>
          <button type="button" className="icon-button -me-2 -mt-2" onClick={onClose} aria-label={t('common.close')}>
            <X size={18} aria-hidden="true" />
          </button>
        </div>
        <div className="mt-4 min-h-0 overflow-y-auto text-sm leading-7 text-muted dark:text-slate-300">{children}</div>
        {actions && <div className="mt-6 flex flex-wrap justify-end gap-3">{actions}</div>}
      </div>
    </div>
  )
}
