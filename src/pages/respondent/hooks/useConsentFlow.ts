import { useEffect, useState } from 'react'
import {
  fetchSurveyPreview,
  getSessionState,
  giveConsent,
  startSession,
} from '../api/respondentApi'
import type { SurveyPreview } from '../api/respondent.mapper'
import {
  clearLegacySessionKey,
  clearSessionRestore,
  readSessionRestore,
  writeSessionRestore,
} from '../storage'

type ApiError = { status?: number; detail?: string }

export type ConsentFlowState = {
  token: string | null
  preview: SurveyPreview | null
  isLoadingPreview: boolean
  loadError: string | null
  loadErrorStatus: number | null
  isAccepted: boolean
  setAccepted: (value: boolean) => void
  isSubmitting: boolean
  submitError: string | null
  submit: () => Promise<void>
  restartAvailable: boolean
  restart: () => void
  restoredSessionId: string | null
}

function extractToken(): string | null {
  const segments = window.location.pathname.split('/').filter(Boolean)
  if (segments.length < 2 || segments[0] !== 's') return null
  return segments[1]
}

function redirectToChat(sessionId: string): void {
  window.location.href = `/chat/${encodeURIComponent(sessionId)}`
}

function redirectToResult(sessionId: string): void {
  window.location.href = `/chat/${encodeURIComponent(sessionId)}/result`
}

export function useConsentFlow(): ConsentFlowState {
  const [token] = useState<string | null>(() => extractToken())
  const [preview, setPreview] = useState<SurveyPreview | null>(null)
  const [isLoadingPreview, setIsLoadingPreview] = useState<boolean>(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [loadErrorStatus, setLoadErrorStatus] = useState<number | null>(null)
  const [isAccepted, setAccepted] = useState<boolean>(false)
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [restartAvailable, setRestartAvailable] = useState<boolean>(false)
  const [restoredSessionId, setRestoredSessionId] = useState<string | null>(null)
  const [restartTick, setRestartTick] = useState<number>(0)

  useEffect(() => {
    let active = true
    clearLegacySessionKey()
    async function load() {
      if (!token) {
        if (!active) return
        setLoadError('Ссылка некорректна')
        setLoadErrorStatus(400)
        setIsLoadingPreview(false)
        return
      }

      setIsLoadingPreview(true)
      setLoadError(null)
      setLoadErrorStatus(null)
      setRestartAvailable(false)
      setRestoredSessionId(null)

      try {
        const data = await fetchSurveyPreview(token)
        if (!active) return
        setPreview(data)
      } catch (err: unknown) {
        if (!active) return
        const apiErr = err as ApiError
        setLoadError(apiErr.detail ?? 'Не удалось загрузить опрос')
        setLoadErrorStatus(apiErr.status ?? 500)
        setIsLoadingPreview(false)
        return
      }

      const restore = readSessionRestore(token)
      if (!restore) {
        if (active) setIsLoadingPreview(false)
        return
      }

      try {
        const state = await getSessionState(restore.sessionId)
        if (!active) return
        if (state.status === 'completed') {
          redirectToResult(restore.sessionId)
          return
        }
        if (state.status === 'in_progress') {
          redirectToChat(restore.sessionId)
          return
        }
        if (state.status === 'consent_pending') {
          setRestoredSessionId(restore.sessionId)
          setIsLoadingPreview(false)
          return
        }
        setRestartAvailable(true)
        setRestoredSessionId(restore.sessionId)
        setIsLoadingPreview(false)
      } catch (err: unknown) {
        if (!active) return
        const apiErr = err as ApiError
        if (apiErr.status === 404) {
          clearSessionRestore(token)
        }
        setIsLoadingPreview(false)
      }
    }
    void load()
    return () => {
      active = false
    }
  }, [token, restartTick])

  async function submit(): Promise<void> {
    if (!token || isSubmitting || !isAccepted) return
    setIsSubmitting(true)
    setSubmitError(null)
    try {
      let sessionId: string
      if (restoredSessionId && !restartAvailable) {
        sessionId = restoredSessionId
      } else {
        const session = await startSession(token)
        sessionId = session.session_id
      }
      await giveConsent(sessionId)
      writeSessionRestore(token, { sessionId, lastKnownIndex: 0 })
      redirectToChat(sessionId)
    } catch (err: unknown) {
      const apiErr = err as ApiError
      setSubmitError(apiErr.detail ?? 'Не удалось начать опрос')
      setIsSubmitting(false)
    }
  }

  function restart(): void {
    if (token) clearSessionRestore(token)
    setRestoredSessionId(null)
    setRestartAvailable(false)
    setRestartTick((n) => n + 1)
  }

  return {
    token,
    preview,
    isLoadingPreview,
    loadError,
    loadErrorStatus,
    isAccepted,
    setAccepted,
    isSubmitting,
    submitError,
    submit,
    restartAvailable,
    restart,
    restoredSessionId,
  }
}
