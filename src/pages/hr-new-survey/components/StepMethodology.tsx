import { Spinner } from '../../../shared/ui'
import type { MethodologyBrief } from '../../hr-dashboard/api/hrDashboard.mapper'

type Props = {
  methodologies: MethodologyBrief[]
  isLoading: boolean
  loadError: string | null
  selectedId: number | null
  error: string | undefined
  onSelect: (id: number) => void
}

export default function StepMethodology({
  methodologies,
  isLoading,
  loadError,
  selectedId,
  error,
  onSelect,
}: Props) {
  return (
    <section className="new-survey-step-body">
      <h2>Выбор методики</h2>
      <p className="step-hint">
        Методика определяет шкалы, типы вопросов и интерпретацию профиля.
      </p>
      {isLoading ? (
        <div className="step-loading">
          <Spinner />
          <span>Загружаем доступные методики…</span>
        </div>
      ) : loadError ? (
        <p className="step-error">{loadError}</p>
      ) : methodologies.length === 0 ? (
        <p className="step-empty">
          Опубликованных методик пока нет. Попросите администратора опубликовать
          методику.
        </p>
      ) : (
        <ul className="methodology-list">
          {methodologies.map((m) => {
            const isSelected = m.id === selectedId
            return (
              <li key={m.id}>
                <button
                  type="button"
                  className={`methodology-card${isSelected ? ' is-selected' : ''}`}
                  onClick={() => onSelect(m.id)}
                  aria-pressed={isSelected}
                >
                  <div className="methodology-card-head">
                    <span className="methodology-name">{m.name}</span>
                    {m.category ? (
                      <span className="methodology-category">{m.category}</span>
                    ) : null}
                  </div>
                  <p className="methodology-meta">
                    {m.scaleCount} шкал · ID #{m.id}
                  </p>
                </button>
              </li>
            )
          })}
        </ul>
      )}
      {error ? <p className="step-error">{error}</p> : null}
    </section>
  )
}
