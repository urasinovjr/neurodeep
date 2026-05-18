import { useMemo } from 'react'
import { Spinner } from '../../shared/ui'
import EmptyState from './components/EmptyState'
import Filters from './components/Filters'
import SurveyCard from './components/SurveyCard'
import { useDashboardData } from './hooks/useDashboardData'
import { useDashboardFilters } from './hooks/useDashboardFilters'
import './dashboard.css'

export default function HrDashboardPage() {
  const filterApi = useDashboardFilters()
  const data = useDashboardData(filterApi.filters)

  const methodologyById = useMemo(() => {
    const map = new Map<number, string>()
    data.methodologies.forEach((m) => map.set(m.id, m.name))
    return map
  }, [data.methodologies])

  const hasActiveFilters =
    filterApi.filters.status !== '' ||
    filterApi.filters.methodologyId !== undefined

  const totalPages = data.surveys
    ? Math.max(1, Math.ceil(data.surveys.total / data.pageSize))
    : 1
  const currentPage = filterApi.filters.page
  const items = data.surveys?.items ?? []
  const totalItems = data.surveys?.total ?? 0

  return (
    <main className="dashboard-page">
      <div className="dashboard-shell">
        <header className="dashboard-header">
          <div>
            <h1>Мои исследования</h1>
            <p className="dashboard-subtitle">
              Управление опросами, приглашениями и аналитикой по методикам.
            </p>
          </div>
          <a className="dashboard-cta" href="/hr/surveys/new">
            Новое исследование
          </a>
        </header>

        <Filters
          filters={filterApi.filters}
          methodologies={data.methodologies}
          onStatus={filterApi.setStatus}
          onMethodology={filterApi.setMethodology}
          onSort={filterApi.setSort}
          onToggleSortDir={filterApi.toggleSortDir}
        />

        {data.isLoadingSurveys ? (
          <section className="dashboard-loading">
            <Spinner />
            <p>Загружаем исследования…</p>
          </section>
        ) : data.error ? (
          <section className="dashboard-error">
            <h2>Не удалось загрузить</h2>
            <p>{data.error}</p>
          </section>
        ) : items.length === 0 ? (
          <EmptyState hasFilters={hasActiveFilters} onReset={filterApi.reset} />
        ) : (
          <>
            <p className="dashboard-counter">
              Всего: {totalItems} · страница {currentPage} из {totalPages}
            </p>
            <section className="dashboard-grid" data-testid="dashboard-grid">
              {items.map((survey) => (
                <SurveyCard
                  key={survey.id}
                  survey={survey}
                  methodologyName={
                    methodologyById.get(survey.methodologyId) ?? null
                  }
                />
              ))}
            </section>
            {totalPages > 1 ? (
              <nav className="dashboard-pagination">
                <button
                  type="button"
                  className="pagination-button"
                  disabled={currentPage <= 1}
                  onClick={() => filterApi.setPage(currentPage - 1)}
                >
                  ← Назад
                </button>
                <span className="pagination-info">
                  {currentPage} / {totalPages}
                </span>
                <button
                  type="button"
                  className="pagination-button"
                  disabled={currentPage >= totalPages}
                  onClick={() => filterApi.setPage(currentPage + 1)}
                >
                  Вперёд →
                </button>
              </nav>
            ) : null}
          </>
        )}
      </div>
    </main>
  )
}
