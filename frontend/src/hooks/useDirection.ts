import { useLayoutEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { applyDocumentLanguage, persistLanguage, type Language } from '../lib/i18n'

export function useDirection(): Language {
  const { i18n } = useTranslation()
  const language: Language = i18n.resolvedLanguage === 'ar' ? 'ar' : 'en'

  // Layout effect: the new direction is applied before the browser paints the switched text.
  useLayoutEffect(() => {
    applyDocumentLanguage(language)
    persistLanguage(language)
  }, [language])

  return language
}
