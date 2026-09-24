import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import ar from '../locales/ar/translation.json'
import en from '../locales/en/translation.json'

export type Language = 'en' | 'ar'
const LANGUAGE_KEY = 'abdullah-kit-language'

function savedLanguage(): Language {
  try {
    return window.localStorage.getItem(LANGUAGE_KEY) === 'ar' ? 'ar' : 'en'
  } catch {
    return 'en'
  }
}

export function persistLanguage(language: Language): void {
  try {
    window.localStorage.setItem(LANGUAGE_KEY, language)
  } catch {
    // The preference is optional when storage is disabled.
  }
}

export function applyDocumentLanguage(language: Language): void {
  document.documentElement.lang = language
  document.documentElement.dir = language === 'ar' ? 'rtl' : 'ltr'
}

const initialLanguage = savedLanguage()
// Set the root direction before React renders so Arabic never paints one LTR frame.
applyDocumentLanguage(initialLanguage)

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, ar: { translation: ar } },
  lng: initialLanguage,
  fallbackLng: 'en',
  supportedLngs: ['en', 'ar'],
  interpolation: { escapeValue: false },
  react: { useSuspense: false },
})

export default i18n
