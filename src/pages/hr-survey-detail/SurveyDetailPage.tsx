import { useMemo } from 'react'
import { Spinner } from '../../shared/ui'
import type { MethodologyBrief } from '../../shared/types/methodology'
import { useMethodologies } from '../../shared/hooks/useMethodologies'
import ActionsBlock from './components/ActionsBlock'
import InviteBlock from './components/InviteBlock'
import QrBlock from './components/QrBlock'
import SurveyMeta from './components/SurveyMeta'
import { useSurveyDetail } from './hooks/useSurveyDetail'
import './survey-detail.css'

function buildInviteUrl(token: string): string {
  return `${window.location.origin}/s/${encodeURIComponent(token)}`
}

export default function SurveyDetailPage() {
  const detailState = useSurveyDetail()
  const methodologiesState = useMethodologies()

  const { methodologies } = methodologiesState
  const methodologyById = useMemo(() => {
    const map = new Map<number, MethodologyBrief>()
    methodologies.forEach((m) => map.set(m.id, m))
    return map
  }, [methodologies])

  if (detailState.isLoading) {
    return (
      <main className="detail-page">
        <div className="detail-shell">
          <section className="detail-loading">
            <Spinner />
            <p>Загружаем исследование…</p>
          </section>
        </div>
      </main>
    )
  }

  if (detailState.error) {
    return (
      <main className="detail-page">
        <div className="detail-shell">
          <a className="back-link" href="/hr/dashboard">
            ← К дашборду
          </a>
          <section className="detail-error-card">
            <h1>Не удалось открыть исследование</h1>
            <p>{detailState.error.message}</p>
            {detailState.error.kind === 'network' ? (
              <button
                type="button"
                className="text-button"
                onClick={detailState.reload}
              >
                Попробовать ещё раз
              </button>
            ) : null}
          </section>
        </div>
      </main>
    )
  }

  if (!detailState.detail) return null

  const detail = detailState.detail
  const inviteUrl = buildInviteUrl(detail.inviteToken)
  const filename = `psychograph-survey-${detail.id}-qr.png`

  return (
    <main className="detail-page">
      <div className="detail-shell">
        <a className="back-link" href="/hr/dashboard">
          ← К дашборду
        </a>

        <SurveyMeta
          detail={detail}
          methodology={methodologyById.get(detail.methodologyId)}
        />

        <InviteBlock inviteUrl={inviteUrl} disabled={detail.status === 'archived'} />

        <QrBlock inviteUrl={inviteUrl} filename={filename} />

        <ActionsBlock
          status={detail.status}
          surveyId={detail.id}
          isArchiving={detailState.isArchiving}
          archiveError={detailState.archiveError}
          onArchive={() => void detailState.archive()}
        />
      </div>
    </main>
  )
}
