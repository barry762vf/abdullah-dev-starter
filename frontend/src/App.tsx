import { useEffect, useLayoutEffect } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { useDirection } from './hooks/useDirection'
import { queryClient } from './lib/queryClient'
import { subscribeSession } from './lib/api'
import { currentUserKey } from './features/auth/useCurrentUser'
import { AppRoutes } from './routes/AppRoutes'
import { useUiStore } from './stores/uiStore'

function AppEffects() {
  useDirection()
  const theme = useUiStore((state) => state.theme)

  useLayoutEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    try { window.localStorage.setItem('abdullah-kit-theme', theme) } catch { /* optional preference */ }
  }, [theme])

  useEffect(() => subscribeSession((signal) => {
    if (signal === 'signed-out') {
      void queryClient.cancelQueries({ queryKey: currentUserKey })
      queryClient.setQueryData(currentUserKey, null)
      queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== currentUserKey[0] })
    } else if (signal === 'auth-updated') {
      void queryClient.invalidateQueries({ queryKey: currentUserKey })
    }
  }), [])

  return <AppRoutes />
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppEffects />
      </BrowserRouter>
    </QueryClientProvider>
  )
}
