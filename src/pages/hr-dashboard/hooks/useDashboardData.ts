import { useEffect, useState } from 'react'
import { fetchSurveys } from '../api/hrDashboardApi'
import { useMethodologies } from '../../../shared/hooks/useMethodologies'
import type { MethodologyBrief } from '../../../shared/types/methodology'
import type { SurveyList } from '../api/hrDashboard.mapper'
import type { DashboardFilters } from './useDashboardFilters'

const PAGE_SIZE = 12

type ApiError = { status?: number; detail?: string }

export type UseDashboardData = {
  surveys: SurveyList | null
  methodologies: MethodologyBrief[]
  isLoadingSurveys: boolean
  isLoadingMethodologies: boolean
  error: string | null
  pageSize: number
}

function describeError(err: ApiError): string {
  if (err.status === 401 || err.status === 403) {
    return 'Доступ запрещён. Войдите как researcher или admin.'
  }
  return err.detail ?? 'Не удалось загрузить исследования.'
}

export function useDashboardData(filters: DashboardFilters): UseDashboardData {
  const [surveys, setSurveys] = useState<SurveyList | null>(null)
  const methodologiesState = useMethodologies()
  const [isLoadingSurveys, setIsLoadingSurveys] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    async function load(): Promise<void> {
      if (!active) return
      setIsLoadingSurveys(true)
      setError(null)
      try {
        const result = await fetchSurveys({
          status: filters.status || undefined,
          methodologyId: filters.methodologyId,
          sort: filters.sort,
          sortDir: filters.sortDir,
          limit: PAGE_SIZE,
          offset: (filters.page - 1) * PAGE_SIZE,
        })
        if (!active) return
        setSurveys(result)
      } catch (err: unknown) {
        if (!active) return
        setError(describeError(err as ApiError))
      } finally {
        if (active) setIsLoadingSurveys(false)
      }
    }
    void load()
    return () => {
      active = false
    }
  }, [
    filters.status,
    filters.methodologyId,
    filters.sort,
    filters.sortDir,
    filters.page,
  ])

  return {
    surveys,
    methodologies: methodologiesState.methodologies,
    isLoadingSurveys,
    isLoadingMethodologies: methodologiesState.isLoading,
    error,
    pageSize: PAGE_SIZE,
  }
}
