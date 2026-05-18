import type { NewSurveyDraft } from '../storage'
import type { MethodologyBrief } from '../../../shared/types/methodology'
import { formatDate } from '../../../shared/utils'

type Props = {
  draft: NewSurveyDraft
  methodologies: MethodologyBrief[]
}

export default function StepReview({ draft, methodologies }: Props) {
  const methodology = methodologies.find((m) => m.id === draft.methodologyId)
  return (
    <section className="new-survey-step-body">
      <h2>Проверка перед созданием</h2>
      <p className="step-hint">
        Проверьте параметры. После нажатия «Создать исследование» оно
        зарегистрируется и получит уникальный invite-токен для приглашений.
      </p>
      <dl className="review-grid">
        <div>
          <dt>Название</dt>
          <dd>{draft.name.trim() || '—'}</dd>
        </div>
        <div>
          <dt>Методика</dt>
          <dd>
            {methodology
              ? `${methodology.name} · ${methodology.scaleCount} шкал`
              : '—'}
          </dd>
        </div>
        <div>
          <dt>Старт</dt>
          <dd>{formatDate(draft.startDate, { withTime: true })}</dd>
        </div>
        <div>
          <dt>Окончание</dt>
          <dd>{formatDate(draft.endDate, { withTime: true })}</dd>
        </div>
        <div className="review-wide">
          <dt>Приветствие</dt>
          <dd>{draft.welcomeMessage.trim() || '— (используется значение по умолчанию)'}</dd>
        </div>
        <div className="review-wide">
          <dt>Делиться индивидуально</dt>
          <dd>{draft.allowIndividualShare ? 'Да' : 'Нет'}</dd>
        </div>
      </dl>
    </section>
  )
}
