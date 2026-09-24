import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { ApiError } from '../../lib/api'
import { StatePanel } from '../../components/feedback/StatePanel'
import { useCurrentUser } from './useCurrentUser'

export function AuthGuard() {
  const location = useLocation()
  const { data, isPending, error, refetch } = useCurrentUser()

  if (isPending) return <StatePanel kind="loading" />
  if (error instanceof ApiError && error.status === 401) {
    return <Navigate to="/login" replace state={{ from: location.pathname, messageKey: 'auth.sessionExpired' }} />
  }
  if (error) return <StatePanel kind="error" onRetry={() => void refetch()} />
  if (!data) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return <Outlet />
}
