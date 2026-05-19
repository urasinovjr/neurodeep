import { Button } from '../../../shared/ui'

type Props = {
  hasFilters: boolean
  onReset: () => void
}

export default function EmptyState({ hasFilters, onReset }: Props) {
  if (hasFilters) {
    return (
      <section className="dashboard-empty" data-testid="dashboard-empty-filtered">
        <h2>Ничего не нашлось</h2>
        <p>
          Под выбранные фильтры исследования не подходят. Попробуйте сбросить
          фильтры.
        </p>
        <Button type="button" variant="secondary" onClick={onReset}>
          Сбросить фильтры
        </Button>
      </section>
    )
  }
  return (
    <section className="dashboard-empty" data-testid="dashboard-empty">
      <h2>У вас пока нет исследований</h2>
      <p>
        Создайте первое исследование — настройте методику, отправьте сотрудникам
        приглашения и получите агрегированную аналитику.
      </p>
      <a className="dashboard-empty-cta" href="/hr/surveys/new">
        Создать первое исследование
      </a>
    </section>
  )
}
