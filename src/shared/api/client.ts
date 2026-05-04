const API_BASE: string = import.meta.env.VITE_API_BASE_URL ?? '/api'

let accessToken: string | null = null
let refreshPromise: Promise<boolean> | null = null

export function setAccessToken(token: string | null): void {
  accessToken = token
}

export function getAccessToken(): string | null {
  return accessToken
}

export type ApiError = {
  status: number
  detail: string
}

type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'DELETE'

type RequestOptions = {
  headers?: Record<string, string>
  signal?: AbortSignal
}

function readCsrfToken(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/)
  return match ? decodeURIComponent(match[1]) : null
}

async function refreshAccessToken(): Promise<boolean> {
  if (refreshPromise) return refreshPromise
  refreshPromise = (async () => {
    try {
      const csrf = readCsrfToken()
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      if (csrf) headers['X-CSRF-Token'] = csrf
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
        headers,
      })
      if (!response.ok) {
        accessToken = null
        return false
      }
      const data = (await response.json()) as { access_token?: string }
      if (typeof data.access_token === 'string' && data.access_token.length > 0) {
        accessToken = data.access_token
        return true
      }
      accessToken = null
      return false
    } catch {
      accessToken = null
      return false
    } finally {
      refreshPromise = null
    }
  })()
  return refreshPromise
}

async function readErrorDetail(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: unknown }
    if (typeof data?.detail === 'string') return data.detail
    return response.statusText || 'Ошибка запроса'
  } catch {
    return response.statusText || 'Ошибка запроса'
  }
}

function buildRequestInit(
  method: HttpMethod,
  body: unknown,
  options: RequestOptions,
  token: string | null,
): RequestInit {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...options.headers,
  }
  if (token) headers.Authorization = `Bearer ${token}`
  return {
    method,
    headers,
    credentials: 'include',
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal: options.signal,
  }
}

async function request<T>(
  method: HttpMethod,
  path: string,
  body?: unknown,
  options: RequestOptions = {},
): Promise<T> {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`

  let response = await fetch(url, buildRequestInit(method, body, options, accessToken))

  if (response.status === 401 && !path.startsWith('/auth/refresh')) {
    const refreshed = await refreshAccessToken()
    if (refreshed) {
      response = await fetch(url, buildRequestInit(method, body, options, accessToken))
    }
  }

  if (!response.ok) {
    const detail = await readErrorDetail(response)
    const error: ApiError = { status: response.status, detail }
    throw error
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const apiClient = {
  get: <T>(path: string, options?: RequestOptions): Promise<T> =>
    request<T>('GET', path, undefined, options),
  post: <T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> =>
    request<T>('POST', path, body, options),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> =>
    request<T>('PATCH', path, body, options),
  delete: <T>(path: string, options?: RequestOptions): Promise<T> =>
    request<T>('DELETE', path, undefined, options),
}
