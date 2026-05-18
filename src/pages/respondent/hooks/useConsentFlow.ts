import { useEffect, useState } from 'react'
import {
  fetchSurveyPreview,
  giveConsent,
  startSession,
} from '../api/respondentApi'
import type { SurveyPreview } from '../api/respondent.mapper'

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
}

function extractToken(): string | null {
  const segments = window.location.pathname.split('/').filter(Boolean)
  if (segments.length < 2 || segments[0] !== 's') return null
  return segments[1]
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

  useEffect(() => {
    let active = true
    async function load() {
      if (!token) {
        if (!active) return
        setLoadError('Ссылка некорректна')
        setLoadErrorStatus(400)
        setIsLoadingPreview(false)
        return
      }
      try {
        const data = await fetchSurveyPreview(token)
        if (!active) return
        setPreview(data)
      } catch (err: unknown) {
        if (!active) return
        const apiErr = err as ApiError
        setLoadError(apiErr.detail ?? 'Не удалось загрузить опрос')
        setLoadErrorStatus(apiErr.status ?? 500)
      } finally {
        if (active) setIsLoadingPreview(false)
      }
    }
    void load()
    return () => {
      active = false
    }
  }, [token])

  async function submit(): Promise<void> {
    if (!token || isSubmitting || !isAccepted) return
    setIsSubmitting(true)
    setSubmitError(null)
    try {
      const session = await startSession(token)
      await giveConsent(session.session_id)
      window.location.href = `/chat/${session.session_id}`
    } catch (err: unknown) {
      const apiErr = err as ApiError
      setSubmitError(apiErr.detail ?? 'Не удалось начать опрос')
      setIsSubmitting(false)
    }
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
  }
}
