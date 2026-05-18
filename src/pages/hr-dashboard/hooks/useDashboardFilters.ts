import { useState } from 'react'

export type DashboardFilters = {
  status: string
  methodologyId: number | undefined
  sort: 'created_at' | 'completion_rate'
  sortDir: 'asc' | 'desc'
  page: number
}

export const DEFAULT_FILTERS: DashboardFilters = {
  status: '',
  methodologyId: undefined,
  sort: 'created_at',
  sortDir: 'desc',
  page: 1,
}

export type UseDashboardFilters = {
  filters: DashboardFilters
  setStatus: (value: string) => void
  setMethodology: (value: number | undefined) => void
  setSort: (value: 'created_at' | 'completion_rate') => void
  toggleSortDir: () => void
  setPage: (value: number) => void
  reset: () => void
}

export function useDashboardFilters(): UseDashboardFilters {
  const [filters, setFilters] = useState<DashboardFilters>(DEFAULT_FILTERS)
  return {
    filters,
    setStatus: (value) =>
      setFilters((prev) => ({ ...prev, status: value, page: 1 })),
    setMethodology: (value) =>
      setFilters((prev) => ({ ...prev, methodologyId: value, page: 1 })),
    setSort: (value) =>
      setFilters((prev) => ({ ...prev, sort: value, page: 1 })),
    toggleSortDir: () =>
      setFilters((prev) => ({
        ...prev,
        sortDir: prev.sortDir === 'desc' ? 'asc' : 'desc',
        page: 1,
      })),
    setPage: (value) => setFilters((prev) => ({ ...prev, page: value })),
    reset: () => setFilters(DEFAULT_FILTERS),
  }
}
