import { Button } from '../../../shared/ui'

type Props = {
  status: string
  surveyId: number
  isArchiving: boolean
  archiveError: string | null
  onArchive: () => void
}

export default function ActionsBlock({
  status,
  surveyId,
  isArchiving,
  archiveError,
  onArchive,
}: Props) {
  const canArchive = status === 'active'
  return (
    <section className="detail-card">
      <h2>Действия</h2>
      <div className="actions-row">
        <a
          className="action-link"
          href={`/hr/surveys/${surveyId}/analytics`}
        >
          Аналитика →
        </a>
        {canArchive ? (
          <Button
            type="button"
            variant="secondary"
            isLoading={isArchiving}
            onClick={() => {
              if (window.confirm('Архивировать исследование? Респонденты больше не смогут пройти опрос.')) {
                onArchive()
              }
            }}
          >
            Архивировать
          </Button>
        ) : (
          <p className="detail-hint detail-hint-inline">
            {status === 'archived'
              ? 'Архивировано. Респонденты больше не смогут пройти опрос.'
              : status === 'draft'
                ? 'Это черновик. Когда вы активируете исследование, респонденты смогут пройти его по ссылке.'
                : 'Действия недоступны для этого статуса.'}
          </p>
        )}
      </div>
      {archiveError ? <p className="detail-error">{archiveError}</p> : null}
    </section>
  )
}
