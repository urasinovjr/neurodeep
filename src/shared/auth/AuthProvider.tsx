import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'

import { apiClient, setAccessToken } from '../api'
import {
  AuthContext,
  type AuthState,
  type RegisterPayload,
  type User,
  type UserRole,
  type UserStatus,
} from './AuthContext'

type AuthProviderProps = {
  children: ReactNode
}

type UserResponseDto = {
  id: number
  email: string
  first_name: string
  last_name: string
  role: string
  status: string
  email_verified: boolean
}

type TokenResponseDto = {
  access_token: string
  token_type?: string
}

const KNOWN_ROLES: readonly UserRole[] = ['pending', 'respondent', 'researcher', 'admin']
const KNOWN_STATUSES: readonly UserStatus[] = ['active', 'blocked']

function mapUser(dto: UserResponseDto): User {
  const role = KNOWN_ROLES.includes(dto.role as UserRole) ? (dto.role as UserRole) : 'pending'
  const status = KNOWN_STATUSES.includes(dto.status as UserStatus) ? (dto.status as UserStatus) : 'active'
  return {
    id: dto.id,
    email: dto.email,
    firstName: dto.first_name,
    lastName: dto.last_name,
    role,
    status,
    emailVerified: dto.email_verified,
  }
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let active = true
    async function loadCurrent() {
      try {
        const me = await apiClient.get<UserResponseDto>('/auth/me')
        if (!active) return
        setUser(mapUser(me))
      } catch {
        if (!active) return
        setUser(null)
        setAccessToken(null)
      } finally {
        if (active) setIsLoading(false)
      }
    }
    void loadCurrent()
    return () => {
      active = false
    }
  }, [])

  async function login(email: string, password: string): Promise<User> {
    const tokens = await apiClient.post<TokenResponseDto>('/auth/login', { email, password })
    setAccessToken(tokens.access_token)
    const me = await apiClient.get<UserResponseDto>('/auth/me')
    const mapped = mapUser(me)
    setUser(mapped)
    return mapped
  }

  async function register(payload: RegisterPayload): Promise<User> {
    const dto = await apiClient.post<UserResponseDto>('/auth/register', {
      email: payload.email,
      password: payload.password,
      first_name: payload.firstName,
      last_name: payload.lastName,
      invite_token: payload.inviteToken ?? null,
    })
    return mapUser(dto)
  }

  async function logout(): Promise<void> {
    try {
      await apiClient.post<void>('/auth/logout')
    } finally {
      setAccessToken(null)
      setUser(null)
    }
  }

  async function verifyEmail(token: string): Promise<void> {
    const query = new URLSearchParams({ token }).toString()
    await apiClient.post<void>(`/auth/verify-email?${query}`)
  }

  async function requestPasswordReset(email: string): Promise<void> {
    await apiClient.post<void>('/auth/password-reset-request', { email })
  }

  async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
    await apiClient.post<void>('/auth/change-password', {
      old_password: oldPassword,
      new_password: newPassword,
    })
  }

  async function resetPassword(resetToken: string, newPassword: string): Promise<void> {
    await apiClient.post<void>('/auth/change-password', {
      reset_token: resetToken,
      new_password: newPassword,
    })
  }

  const value: AuthState = {
    user,
    isLoading,
    login,
    register,
    logout,
    verifyEmail,
    requestPasswordReset,
    changePassword,
    resetPassword,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
