import { useCallback, useEffect, useState } from 'react'
import {
  archiveSurvey,
  fetchSurveyDetail,
} from '../api/surveyDetailApi'
import type { SurveyDetail } from '../api/surveyDetail.mapper'

type ApiError = { status?: number; detail?: string }

export type SurveyDetailError = {
  kind: 'invalid_id' | 'not_found' | 'forbidden' | 'network'
  message: string
}

export type UseSurveyDetail = {
  surveyId: number | null
  detail: SurveyDetail | null
  isLoading: boolean
  error: SurveyDetailError | null
  isArchiving: boolean
  archiveError: string | null
  reload: () => void
  archive: () => Promise<void>
}

function extractSurveyId(): number | null {
  const match = window.location.pathname.match(/^\/hr\/surveys\/(\d+)$/)
  if (!match) return null
  const parsed = Number(match[1])
  return Number.isFinite(parsed) ? parsed : null
}

function describeError(err: ApiError): SurveyDetailError {
  if (err.status === 404) {
    return {
      kind: 'not_found',
      message: 'Исследование не найдено. Возможно, оно было удалено.',
    }
  }
  if (err.status === 403) {
    return {
      kind: 'forbidden',
      message: 'Это исследование принадлежит другому researcher.',
    }
  }
  return {
    kind: 'network',
    message: err.detail ?? 'Не удалось загрузить детали исследования.',
  }
}

const INVALID_ID_ERROR: SurveyDetailError = {
  kind: 'invalid_id',
  message: 'Некорректный ID исследования в ссылке.',
}

export function useSurveyDetail(): UseSurveyDetail {
  const [surveyId] = useState<number | null>(() => extractSurveyId())
  const [detail, setDetail] = useState<SurveyDetail | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(() => surveyId !== null)
  const [error, setError] = useState<SurveyDetailError | null>(() =>
    surveyId === null ? INVALID_ID_ERROR : null,
  )
  const [reloadNonce, setReloadNonce] = useState<number>(0)
  const [isArchiving, setIsArchiving] = useState<boolean>(false)
  const [archiveError, setArchiveError] = useState<string | null>(null)

  useEffect(() => {
    if (!surveyId) return
    let active = true
    async function load(): Promise<void> {
      if (!active) return
      setIsLoading(true)
      setError(null)
      try {
        const data = await fetchSurveyDetail(surveyId!)
        if (!active) return
        setDetail(data)
      } catch (err: unknown) {
        if (!active) return
        setError(describeError(err as ApiError))
      } finally {
        if (active) setIsLoading(false)
      }
    }
    void load()
    return () => {
      active = false
    }
  }, [surveyId, reloadNonce])

  const archive = useCallback(async (): Promise<void> => {
    if (!surveyId) return
    setIsArchiving(true)
    setArchiveError(null)
    try {
      const updated = await archiveSurvey(surveyId)
      setDetail(updated)
    } catch (err: unknown) {
      const apiErr = err as ApiError
      setArchiveError(apiErr.detail ?? 'Не удалось архивировать исследование.')
    } finally {
      setIsArchiving(false)
    }
  }, [surveyId])

  return {
    surveyId,
    detail,
    isLoading,
    error,
    isArchiving,
    archiveError,
    reload: () => setReloadNonce((n) => n + 1),
    archive,
  }
}
