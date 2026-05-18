import type { MethodologyBrief } from '../api/hrDashboard.mapper'
import type { DashboardFilters } from '../hooks/useDashboardFilters'

type Props = {
  filters: DashboardFilters
  methodologies: MethodologyBrief[]
  onStatus: (value: string) => void
  onMethodology: (value: number | undefined) => void
  onSort: (value: 'created_at' | 'completion_rate') => void
  onToggleSortDir: () => void
}

const STATUS_OPTIONS: Array<{ value: string; label: string }> = [
  { value: '', label: 'Все статусы' },
  { value: 'draft', label: 'Черновик' },
  { value: 'active', label: 'Активно' },
  { value: 'archived', label: 'В архиве' },
  { value: 'completed', label: 'Завершено' },
]

export default function Filters({
  filters,
  methodologies,
  onStatus,
  onMethodology,
  onSort,
  onToggleSortDir,
}: Props) {
  return (
    <section className="dashboard-filters" data-testid="dashboard-filters">
      <label className="filter-field">
        <span className="filter-label">Статус</span>
        <select
          className="filter-input"
          value={filters.status}
          onChange={(event) => onStatus(event.target.value)}
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </label>

      <label className="filter-field">
        <span className="filter-label">Методика</span>
        <select
          className="filter-input"
          value={filters.methodologyId ?? ''}
          onChange={(event) => {
            const value = event.target.value
            onMethodology(value === '' ? undefined : Number(value))
          }}
        >
          <option value="">Все методики</option>
          {methodologies.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name}
            </option>
          ))}
        </select>
      </label>

      <label className="filter-field">
        <span className="filter-label">Сортировка</span>
        <select
          className="filter-input"
          value={filters.sort}
          onChange={(event) =>
            onSort(event.target.value as 'created_at' | 'completion_rate')
          }
        >
          <option value="created_at">По дате создания</option>
          <option value="completion_rate">По проценту прохождения</option>
        </select>
      </label>

      <button
        type="button"
        className="filter-direction"
        onClick={onToggleSortDir}
        aria-label="Поменять направление сортировки"
        title={filters.sortDir === 'desc' ? 'Убывание' : 'Возрастание'}
      >
        {filters.sortDir === 'desc' ? '↓' : '↑'}
      </button>
    </section>
  )
}
