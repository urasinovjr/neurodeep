import { createContext } from 'react'

export type UserRole = 'researcher' | 'admin'

export type User = {
  id: number
  email: string
  role: UserRole
}

export type AuthState = {
  user: User | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  verifyEmail: (token: string) => Promise<void>
  requestPasswordReset: (email: string) => Promise<void>
  changePassword: (oldPassword: string, newPassword: string) => Promise<void>
}

export const AuthContext = createContext<AuthState | null>(null)
