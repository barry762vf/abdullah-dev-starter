import { Outlet } from 'react-router-dom'
import { StatePanel } from '../../components/feedback/StatePanel'
import { useCurrentUser } from '../auth/useCurrentUser'
import { hasRole } from './roles'

/**
 * UX-only route gate, nested inside AuthGuard. It hides screens a user cannot use; it is not a
 * security boundary. Every admin API call is authorized again by the backend from current roles.
 */
export function RoleGuard({ roles }: { roles: readonly string[] }) {
  const { data, isPending, error, refetch } = useCurrentUser()

  if (isPending) return <StatePanel kind="loading" />
  if (error) return <StatePanel kind="error" onRetry={() => void refetch()} />
  if (!hasRole(data, roles)) return <StatePanel kind="forbidden" headingLevel={1} />
  return <Outlet />
}
