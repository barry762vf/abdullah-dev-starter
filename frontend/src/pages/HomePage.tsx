import { ArrowUpRight, Globe2, PlugZap, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

export function HomePage() {
  const { t } = useTranslation()

  return (
    <div className="space-y-7">
      <section className="panel relative overflow-hidden px-7 py-10 sm:px-10 sm:py-14 lg:px-14 lg:py-16">
        <div className="pointer-events-none absolute -end-16 -top-20 size-72 rounded-full bg-blue-100/70 blur-3xl dark:bg-blue-500/10" aria-hidden="true" />
        <div className="relative max-w-2xl">
          <p className="inline-flex items-center gap-2 rounded-full border border-blue-100 bg-blue-50 px-3 py-1.5 text-xs font-bold text-accent dark:border-blue-500/20 dark:bg-blue-500/10 dark:text-blue-300">
            <Sparkles size={14} aria-hidden="true" /> {t('home.eyebrow')}
          </p>
          <h1 className="mt-7 max-w-xl text-4xl font-extrabold leading-[1.16] tracking-tight sm:text-5xl lg:text-[3.5rem]">{t('home.title')}</h1>
          <p className="mt-6 max-w-xl text-base leading-8 text-muted sm:text-lg dark:text-slate-300">{t('home.description')}</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link className="button-primary gap-2" to="/dashboard">{t('home.primaryAction')}<ArrowUpRight className="rtl:-scale-x-100" size={17} aria-hidden="true" /></Link>
            <Link className="button-secondary" to="/register">{t('home.secondaryAction')}</Link>
          </div>
        </div>
      </section>
      <div className="grid gap-5 lg:grid-cols-2">
        <section className="panel p-7 sm:p-8">
          <div className="flex size-11 items-center justify-center rounded-2xl bg-violet-50 text-violet-600 dark:bg-violet-500/10 dark:text-violet-300"><Globe2 size={21} aria-hidden="true" /></div>
          <h2 className="mt-6 text-xl font-bold">{t('home.languageCardTitle')}</h2>
          <p className="mt-3 text-sm leading-7 text-muted dark:text-slate-300">{t('home.languageCardBody')}</p>
        </section>
        <section className="panel p-7 sm:p-8">
          <div className="flex size-11 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-300"><PlugZap size={21} aria-hidden="true" /></div>
          <h2 className="mt-6 text-xl font-bold">{t('home.apiCardTitle')}</h2>
          <p className="mt-3 text-sm leading-7 text-muted dark:text-slate-300">{t('home.apiCardBody')}</p>
        </section>
      </div>
    </div>
  )
}
