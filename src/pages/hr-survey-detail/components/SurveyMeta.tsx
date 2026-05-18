import {
  SURVEY_STATUS_LABEL,
  type MethodologyBrief,
} from '../../hr-dashboard/api/hrDashboard.mapper'
import type { SurveyDetail } from '../api/surveyDetail.mapper'

type Props = {
  detail: SurveyDetail
  methodology: MethodologyBrief | undefined
}

const STATUS_CLASS: Record<string, string> = {
  draft: 'survey-status-draft',
  active: 'survey-status-active',
  archived: 'survey-status-archived',
  completed: 'survey-status-completed',
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  try {
    const date = new Date(iso)
    return new Intl.DateTimeFormat('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date)
  } catch {
    return '—'
  }
}

export default function SurveyMeta({ detail, methodology }: Props) {
  const statusClass = STATUS_CLASS[detail.status] ?? 'survey-status-default'
  const statusLabel = SURVEY_STATUS_LABEL[detail.status] ?? detail.status
  return (
    <section className="detail-meta">
      <div className="detail-meta-head">
        <span className={`survey-status ${statusClass}`}>{statusLabel}</span>
        {detail.invitedCount > 0 ? (
          <span className="detail-rate">
            {Math.round(detail.completionRate * 100)}% прошли
          </span>
        ) : null}
      </div>
      <h1 className="detail-name">{detail.name}</h1>
      <p className="detail-methodology">
        {methodology ? methodology.name : 'Методика не найдена'}
        {methodology ? ` · ${methodology.scaleCount} шкал` : ''}
      </p>
      <dl className="detail-grid">
        <div>
          <dt>Создано</dt>
          <dd>{formatDate(detail.createdAt)}</dd>
        </div>
        <div>
          <dt>Старт</dt>
          <dd>{formatDate(detail.startDate)}</dd>
        </div>
        <div>
          <dt>Окончание</dt>
          <dd>{formatDate(detail.endDate)}</dd>
        </div>
        <div>
          <dt>Приглашено / Завершили</dt>
          <dd>
            {detail.invitedCount > 0
              ? `${detail.completedCount} / ${detail.invitedCount}`
              : `${detail.completedCount} прошли`}
          </dd>
        </div>
        <div className="detail-grid-wide">
          <dt>Индивидуальная отправка</dt>
          <dd>
            {detail.allowIndividualShare
              ? 'Разрешена — респондент может поделиться своим профилем с HR.'
              : 'Запрещена — HR видит только агрегаты.'}
          </dd>
        </div>
        {detail.welcomeMessage ? (
          <div className="detail-grid-wide">
            <dt>Приветствие</dt>
            <dd className="detail-welcome">{detail.welcomeMessage}</dd>
          </div>
        ) : null}
      </dl>
    </section>
  )
}
