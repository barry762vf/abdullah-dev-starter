import { Moon, Sun } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useUiStore } from '../../stores/uiStore'

export function ThemeToggle() {
  const { t } = useTranslation()
  const theme = useUiStore((state) => state.theme)
  const toggle = useUiStore((state) => state.toggleTheme)
  const label = theme === 'dark' ? t('common.lightTheme') : t('common.darkTheme')

  return (
    <button type="button" className="icon-button" onClick={toggle} aria-label={label} title={label}>
      {theme === 'dark' ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
    </button>
  )
}
