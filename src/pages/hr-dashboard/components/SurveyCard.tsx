import type { SurveyListItem } from '../api/hrDashboard.mapper'
import {
  getSurveyStatusClass,
  getSurveyStatusLabel,
} from '../../../shared/constants'
import { formatDate } from '../../../shared/utils'

type Props = {
  survey: SurveyListItem
  methodologyName: string | null
}

function formatPercent(rate: number): string {
  return `${Math.round(rate * 100)}%`
}

export default function SurveyCard({ survey, methodologyName }: Props) {
  const statusClass = getSurveyStatusClass(survey.status)
  const statusLabel = getSurveyStatusLabel(survey.status)
  const completedRatio =
    survey.invitedCount > 0
      ? `${survey.completedCount} / ${survey.invitedCount}`
      : `${survey.completedCount} прошли`
  return (
    <article className="survey-card" data-testid={`survey-card-${survey.id}`}>
      <header className="survey-card-head">
        <span className={`survey-status ${statusClass}`}>{statusLabel}</span>
        {survey.invitedCount > 0 ? (
          <span className="survey-rate">{formatPercent(survey.completionRate)}</span>
        ) : null}
      </header>
      <h3 className="survey-name">{survey.name}</h3>
      <p className="survey-methodology">{methodologyName ?? 'Методика не найдена'}</p>
      <dl className="survey-meta">
        <div>
          <dt>Создано</dt>
          <dd>{formatDate(survey.createdAt)}</dd>
        </div>
        <div>
          <dt>Старт</dt>
          <dd>{formatDate(survey.startDate)}</dd>
        </div>
        <div>
          <dt>Окончание</dt>
          <dd>{formatDate(survey.endDate)}</dd>
        </div>
        <div>
          <dt>Респонденты</dt>
          <dd>{completedRatio}</dd>
        </div>
      </dl>
      <a className="survey-link" href={`/hr/surveys/${survey.id}`}>
        Открыть →
      </a>
    </article>
  )
}
