import { Languages } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { Language } from '../../lib/i18n'

export function LanguageToggle() {
  const { i18n, t } = useTranslation()
  const next: Language = i18n.resolvedLanguage === 'ar' ? 'en' : 'ar'

  return (
    <button
      type="button"
      className="icon-button gap-2 px-3"
      onClick={() => void i18n.changeLanguage(next)}
      title={t('common.language')}
    >
      <Languages size={17} aria-hidden="true" />
      {/* The accessible name keeps the visible label and marks its language for screen readers. */}
      <span className="sr-only">{t('common.language')}: </span>
      <span lang={next} className="text-sm font-semibold">{next === 'ar' ? 'العربية' : 'English'}</span>
    </button>
  )
}
