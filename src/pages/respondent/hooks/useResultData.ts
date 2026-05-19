import { useEffect, useState } from 'react'
import { fetchSessionResult } from '../api/respondentApi'
import type { SessionResult } from '../api/respondent.mapper'

type ApiError = { status?: number; detail?: string }

const POLL_INTERVAL_MS = 1500
const MAX_POLLS = 20

export type ResultLoadError = {
  kind: 'not_found' | 'not_completed' | 'network' | 'unknown'
  message: string
}

export type UseResultData = {
  sessionId: string | null
  result: SessionResult | null
  isLoading: boolean
  isPolling: boolean
  error: ResultLoadError | null
  retry: () => void
}

function extractSessionId(): string | null {
  const segments = window.location.pathname.split('/').filter(Boolean)
  if (segments.length < 3) return null
  if (segments[0] !== 'chat' || segments[2] !== 'result') return null
  return segments[1]
}

function describeError(err: ApiError): ResultLoadError {
  if (err.status === 404) {
    return {
      kind: 'not_found',
      message: 'Сессия не найдена. Возможно, ссылка устарела.',
    }
  }
  if (err.status === 422) {
    return {
      kind: 'not_completed',
      message: 'Опрос ещё не завершён.',
    }
  }
  return {
    kind: 'network',
    message: err.detail ?? 'Не удалось загрузить результаты.',
  }
}

function isProfileReady(result: SessionResult): boolean {
  return result.scaleScores.length > 0
}

const MISSING_SESSION_ERROR: ResultLoadError = {
  kind: 'unknown',
  message: 'Не удалось извлечь идентификатор сессии из ссылки.',
}

export function useResultData(): UseResultData {
  const [sessionId] = useState<string | null>(() => extractSessionId())
  const [result, setResult] = useState<SessionResult | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(() => sessionId !== null)
  const [isPolling, setIsPolling] = useState<boolean>(false)
  const [error, setError] = useState<ResultLoadError | null>(() =>
    sessionId === null ? MISSING_SESSION_ERROR : null,
  )
  const [retryNonce, setRetryNonce] = useState<number>(0)

  useEffect(() => {
    if (!sessionId) return

    let active = true
    let pollTimer: number | null = null
    let pollCount = 0

    const stopPoll = () => {
      if (pollTimer !== null) {
        window.clearTimeout(pollTimer)
        pollTimer = null
      }
    }

    async function load(): Promise<void> {
      try {
        const data = await fetchSessionResult(sessionId!)
        if (!active) return
        setResult(data)
        setError(null)
        if (!isProfileReady(data) && pollCount < MAX_POLLS) {
          setIsPolling(true)
          setIsLoading(false)
          pollCount += 1
          pollTimer = window.setTimeout(() => {
            void load()
          }, POLL_INTERVAL_MS)
          return
        }
        setIsPolling(false)
        setIsLoading(false)
      } catch (err: unknown) {
        if (!active) return
        const apiErr = err as ApiError
        if (apiErr.status === 422 && pollCount < MAX_POLLS) {
          setIsPolling(true)
          setIsLoading(false)
          pollCount += 1
          pollTimer = window.setTimeout(() => {
            void load()
          }, POLL_INTERVAL_MS)
          return
        }
        setIsPolling(false)
        setIsLoading(false)
        setError(describeError(apiErr))
      }
    }

    void load()

    return () => {
      active = false
      stopPoll()
    }
  }, [sessionId, retryNonce])

  return {
    sessionId,
    result,
    isLoading,
    isPolling,
    error,
    retry: () => {
      setError(null)
      setIsLoading(true)
      setRetryNonce((n) => n + 1)
    },
  }
}
