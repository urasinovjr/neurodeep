import {
  getSurveyStatusClass,
  getSurveyStatusLabel,
} from '../../../shared/constants'
import { formatDate } from '../../../shared/utils'
import type { MethodologyBrief } from '../../../shared/types/methodology'
import type { SurveyDetail } from '../api/surveyDetail.mapper'

type Props = {
  detail: SurveyDetail
  methodology: MethodologyBrief | undefined
}

export default function SurveyMeta({ detail, methodology }: Props) {
  const statusClass = getSurveyStatusClass(detail.status)
  const statusLabel = getSurveyStatusLabel(detail.status)
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
          <dd>{formatDate(detail.createdAt, { withTime: true })}</dd>
        </div>
        <div>
          <dt>Старт</dt>
          <dd>{formatDate(detail.startDate, { withTime: true })}</dd>
        </div>
        <div>
          <dt>Окончание</dt>
          <dd>{formatDate(detail.endDate, { withTime: true })}</dd>
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
