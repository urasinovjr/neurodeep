import { useCallback, useEffect, useRef, useState } from 'react'
import {
  getSessionState,
  submitAnswer,
} from '../api/respondentApi'
import type { ChatQuestion, SessionState } from '../api/respondent.mapper'

type ApiError = { status?: number; detail?: string }

export const MIN_ANSWER_LENGTH = 10
const POLL_INTERVAL_MS = 700
const SESSION_STORAGE_KEY = 'psychograph_session_id'

export type LoadFailure = {
  title: string
  body: string
}

export type ChatFlowState = {
  sessionId: string | null
  isLoadingState: boolean
  loadFailure: LoadFailure | null
  currentQuestion: ChatQuestion | null
  nextQuestionIndex: number
  totalQuestions: number
  progressPercent: number
  isProcessing: boolean
  submitError: string | null
  submit: (text: string) => Promise<boolean>
}

function extractSessionId(): string | null {
  const segments = window.location.pathname.split('/').filter(Boolean)
  if (segments.length < 2 || segments[0] !== 'chat') return null
  return segments[1]
}

function describeBadStatus(status: string): LoadFailure {
  if (status === 'consent_pending') {
    return {
      title: 'Сессия не активирована',
      body: 'Вернитесь по ссылке-приглашению и подтвердите согласие, чтобы начать опрос.',
    }
  }
  if (status === 'abandoned') {
    return {
      title: 'Сессия завершена',
      body: 'Эта сессия больше не активна. Откройте ссылку заново, чтобы пройти опрос.',
    }
  }
  return {
    title: 'Сессия недоступна',
    body: 'Состояние сессии не позволяет продолжить опрос.',
  }
}

function describeApiError(err: ApiError): LoadFailure {
  if (err.status === 404) {
    return {
      title: 'Сессия не найдена',
      body: 'Возможно, ссылка устарела. Откройте приглашение заново.',
    }
  }
  return {
    title: 'Не удалось загрузить опрос',
    body: err.detail ?? 'Попробуйте обновить страницу.',
  }
}

export function useChatFlow(): ChatFlowState {
  const [sessionId] = useState<string | null>(() => extractSessionId())
  const [isLoadingState, setIsLoadingState] = useState<boolean>(true)
  const [loadFailure, setLoadFailure] = useState<LoadFailure | null>(null)
  const [currentQuestion, setCurrentQuestion] = useState<ChatQuestion | null>(
    null,
  )
  const [nextQuestionIndex, setNextQuestionIndex] = useState<number>(0)
  const [totalQuestions, setTotalQuestions] = useState<number>(0)
  const [progressPercent, setProgressPercent] = useState<number>(0)
  const [isProcessing, setIsProcessing] = useState<boolean>(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const pollTimerRef = useRef<number | null>(null)

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current !== null) {
      window.clearInterval(pollTimerRef.current)
      pollTimerRef.current = null
    }
  }, [])

  const applyState = useCallback(
    (state: SessionState): 'completed' | 'in_progress' | 'invalid' => {
      if (state.status === 'completed') {
        return 'completed'
      }
      if (state.status !== 'in_progress' || !state.nextQuestion) {
        return 'invalid'
      }
      setCurrentQuestion(state.nextQuestion)
      setNextQuestionIndex(state.nextQuestionIndex)
      setTotalQuestions(state.totalQuestions)
      setProgressPercent(state.progressPercent)
      return 'in_progress'
    },
    [],
  )

  const redirectToResult = useCallback((id: string) => {
    window.location.href = `/chat/${encodeURIComponent(id)}/result`
  }, [])

  useEffect(() => {
    let active = true
    async function load() {
      if (!sessionId) {
        if (active) {
          setLoadFailure({
            title: 'Ссылка некорректна',
            body: 'Не удалось извлечь идентификатор сессии из URL.',
          })
          setIsLoadingState(false)
        }
        return
      }
      try {
        const state = await getSessionState(sessionId)
        if (!active) return
        const result = applyState(state)
        if (result === 'completed') {
          redirectToResult(sessionId)
          return
        }
        if (result === 'invalid') {
          setLoadFailure(describeBadStatus(state.status))
          setIsLoadingState(false)
          return
        }
        try {
          window.localStorage.setItem(SESSION_STORAGE_KEY, sessionId)
        } catch {}
        setIsLoadingState(false)
      } catch (err: unknown) {
        if (!active) return
        setLoadFailure(describeApiError(err as ApiError))
        setIsLoadingState(false)
      }
    }
    void load()
    return () => {
      active = false
    }
  }, [sessionId, applyState, redirectToResult])

  useEffect(() => {
    return () => {
      stopPolling()
    }
  }, [stopPolling])

  const submit = useCallback(
    async (text: string): Promise<boolean> => {
      if (!sessionId || !currentQuestion || isProcessing) return false
      if (text.length < MIN_ANSWER_LENGTH) return false
      setSubmitError(null)
      setIsProcessing(true)
      const answeredQuestionId = currentQuestion.id
      try {
        const ack = await submitAnswer(sessionId, answeredQuestionId, text)
        if (ack.session_status === 'completed') {
          redirectToResult(sessionId)
          return true
        }
      } catch (err: unknown) {
        const apiErr = err as ApiError
        setSubmitError(apiErr.detail ?? 'Не удалось отправить ответ')
        setIsProcessing(false)
        return false
      }
      stopPolling()
      pollTimerRef.current = window.setInterval(async () => {
        try {
          const state = await getSessionState(sessionId)
          if (state.status === 'completed') {
            stopPolling()
            redirectToResult(sessionId)
            return
          }
          if (
            state.status === 'in_progress' &&
            state.nextQuestion &&
            state.nextQuestion.id !== answeredQuestionId
          ) {
            stopPolling()
            applyState(state)
            setIsProcessing(false)
          }
        } catch {}
      }, POLL_INTERVAL_MS)
      return true
    },
    [sessionId, currentQuestion, isProcessing, applyState, redirectToResult, stopPolling],
  )

  return {
    sessionId,
    isLoadingState,
    loadFailure,
    currentQuestion,
    nextQuestionIndex,
    totalQuestions,
    progressPercent,
    isProcessing,
    submitError,
    submit,
  }
}
