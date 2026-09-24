import { AlertCircle, CircleHelp, Inbox, LoaderCircle, LockKeyhole, ShieldAlert } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

type Kind = 'loading' | 'error' | 'empty' | 'unauthorized' | 'forbidden' | 'notFound'

const icons = { loading: LoaderCircle, error: AlertCircle, empty: Inbox, unauthorized: LockKeyhole, forbidden: ShieldAlert, notFound: CircleHelp }

// A full-page state (for example not found) passes headingLevel={1} to keep one page h1.
type Props = { kind: Kind; onRetry?: () => void; headingLevel?: 1 | 2; title?: string; body?: string }

export function StatePanel({ kind, onRetry, headingLevel = 2, ...text }: Props) {
  const { t } = useTranslation()
  const Icon = icons[kind]
  const Heading = headingLevel === 1 ? 'h1' : 'h2'
  const title = text.title ?? (kind === 'empty' ? t('dashboard.emptyTitle') : t(`states.${kind}Title`))
  const body = text.body ?? (kind === 'empty' ? t('dashboard.emptyBody') : t(`states.${kind}Body`))

  return (
    <section className="panel flex min-h-64 flex-col items-center justify-center p-8 text-center" aria-live="polite">
      <div className="flex size-14 items-center justify-center rounded-2xl bg-blue-50 text-accent dark:bg-blue-500/15 dark:text-blue-300">
        <Icon className={kind === 'loading' ? 'animate-spin' : ''} size={25} aria-hidden="true" />
      </div>
      <Heading className="mt-5 text-xl font-bold">{title}</Heading>
      <p className="mt-2 max-w-sm text-sm leading-7 text-muted dark:text-slate-300">{body}</p>
      {kind === 'error' && onRetry && <button type="button" className="button-primary mt-5" onClick={onRetry}>{t('common.tryAgain')}</button>}
      {(kind === 'notFound' || kind === 'forbidden') && <Link className="button-primary mt-5" to="/">{t('common.backHome')}</Link>}
      {kind === 'unauthorized' && <Link className="button-primary mt-5" to="/login">{t('common.signIn')}</Link>}
    </section>
  )
}
