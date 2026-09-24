export type User = {
  id: string
  email: string
  full_name: string
  is_active: boolean
  is_verified: boolean
  roles: string[]
  created_at: string
}

export type LoginInput = { email: string; password: string }
export type RegisterInput = LoginInput & { full_name: string }
