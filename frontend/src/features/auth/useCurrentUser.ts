import { useQuery } from '@tanstack/react-query'
import { getCurrentUser } from '../../lib/api'

export const currentUserKey = ['current-user'] as const

export function useCurrentUser() {
  return useQuery({ queryKey: currentUserKey, queryFn: ({ signal }) => getCurrentUser(signal), retry: false })
}
