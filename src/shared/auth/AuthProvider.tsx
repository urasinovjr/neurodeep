import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'

import { apiClient, setAccessToken } from '../api'
import { AuthContext, type AuthState, type User } from './AuthContext'

type AuthProviderProps = {
  children: ReactNode
}

type AuthResponse = {
  user: User
  access_token: string
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let active = true
    async function loadCurrent() {
      try {
        const me = await apiClient.get<User>('/auth/me')
        if (!active) return
        setUser(me)
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

  async function login(email: string, password: string): Promise<void> {
    const response = await apiClient.post<AuthResponse>('/auth/login', { email, password })
    setAccessToken(response.access_token)
    setUser(response.user)
  }

  async function register(email: string, password: string): Promise<void> {
    const response = await apiClient.post<AuthResponse>('/auth/register', { email, password })
    setAccessToken(response.access_token)
    setUser(response.user)
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
    await apiClient.post<void>('/auth/verify-email', { token })
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

  const value: AuthState = {
    user,
    isLoading,
    login,
    register,
    logout,
    verifyEmail,
    requestPasswordReset,
    changePassword,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
