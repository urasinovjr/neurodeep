import { createContext } from 'react'

export type UserRole = 'pending' | 'respondent' | 'researcher' | 'admin'

export type UserStatus = 'active' | 'blocked'

export type User = {
  id: number
  email: string
  firstName: string
  lastName: string
  role: UserRole
  status: UserStatus
  emailVerified: boolean
}

export type RegisterPayload = {
  email: string
  password: string
  firstName: string
  lastName: string
  inviteToken?: string | null
}

export type AuthState = {
  user: User | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<User>
  register: (payload: RegisterPayload) => Promise<User>
  logout: () => Promise<void>
  verifyEmail: (token: string) => Promise<void>
  requestPasswordReset: (email: string) => Promise<void>
  changePassword: (oldPassword: string, newPassword: string) => Promise<void>
  resetPassword: (resetToken: string, newPassword: string) => Promise<void>
}

export const AuthContext = createContext<AuthState | null>(null)
