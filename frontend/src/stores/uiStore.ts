import { create } from 'zustand'

type Theme = 'light' | 'dark'

function initialTheme(): Theme {
  try {
    return window.localStorage.getItem('abdullah-kit-theme') === 'dark' ? 'dark' : 'light'
  } catch {
    return 'light'
  }
}

type UiState = {
  theme: Theme
  menuOpen: boolean
  toggleTheme: () => void
  setMenuOpen: (open: boolean) => void
}

export const useUiStore = create<UiState>((set) => ({
  theme: initialTheme(),
  menuOpen: false,
  toggleTheme: () => set((state) => ({ theme: state.theme === 'light' ? 'dark' : 'light' })),
  setMenuOpen: (menuOpen) => set({ menuOpen }),
}))
