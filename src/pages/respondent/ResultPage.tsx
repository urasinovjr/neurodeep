import { Spinner } from '../../shared/ui'
import BarsBlock from './components/BarsBlock'
import DownloadButtons from './components/DownloadButtons'
import RadarBlock from './components/RadarBlock'
import WheelBlock from './components/WheelBlock'
import { downloadPinabaUrl } from './api/respondentApi'
import { useResultData } from './hooks/useResultData'
import './result.css'

const LOADING_LINES = [
  'Анализирую ответы…',
  'Нахожу закономерности по шкалам…',
  'Собираю текст профиля…',
]

function buildShareUrl(pinabaUrl: string | null, sessionId: string): string {
  if (pinabaUrl && pinabaUrl.length > 0) {
    if (pinabaUrl.startsWith('http')) return pinabaUrl
    return `${window.location.origin}${pinabaUrl}`
  }
  return `${window.location.origin}/chat/${sessionId}/result`
}

export default function ResultPage() {
  const flow = useResultData()

  if (flow.isLoading) {
    return (
      <main className="result-page">
        <div className="result-shell">
          <section className="result-loading">
            <Spinner />
            <p className="result-loading-title">{LOADING_LINES[0]}</p>
            <p className="result-loading-hint">{LOADING_LINES[1]}</p>
          </section>
        </div>
      </main>
    )
  }

  if (flow.error) {
    return (
      <main className="result-page">
        <div className="result-shell">
          <section className="result-error">
            <h1>Результат недоступен</h1>
            <p>{flow.error.message}</p>
            <button
              type="button"
              className="result-link-button"
              onClick={() => flow.retry()}
            >
              Попробовать ещё раз
            </button>
          </section>
        </div>
      </main>
    )
  }

  if (!flow.result || !flow.sessionId) {
    return (
      <main className="result-page">
        <div className="result-shell">
          <section className="result-loading">
            <Spinner />
            <p className="result-loading-title">Готовим результаты…</p>
          </section>
        </div>
      </main>
    )
  }

  const { result, sessionId } = flow

  if (flow.isPolling && result.scaleScores.length === 0) {
    return (
      <main className="result-page">
        <div className="result-shell">
          <section className="result-loading">
            <Spinner />
            <p className="result-loading-title">{LOADING_LINES[0]}</p>
            <p className="result-loading-hint">{LOADING_LINES[2]}</p>
          </section>
        </div>
      </main>
    )
  }

  const shareUrl = buildShareUrl(result.pinabaUrl, sessionId)
  const interpretation =
    result.textInterpretation ?? result.profileText ?? ''
  const pinabaSrc = result.pinabaUrl ?? downloadPinabaUrl(sessionId)

  return (
    <main className="result-page">
      <div className="result-shell">
        <header className="result-header">
          <h1>Ваш профиль</h1>
          <p className="result-subtitle">
            Текст ваших ответов не сохранён. Ниже — только числовые шкалы и
            интерпретация.
          </p>
        </header>

        <section className="result-charts-row">
          <article className="result-card">
            <h2 className="result-card-title">Радар шкал</h2>
            <RadarBlock scales={result.scaleScores} />
          </article>
          {result.wheelBalance ? (
            <article className="result-card">
              <h2 className="result-card-title">Колесо баланса</h2>
              <WheelBlock wheel={result.wheelBalance} />
            </article>
          ) : null}
        </section>

        <section className="result-card">
          <h2 className="result-card-title">Шкалы</h2>
          <BarsBlock scales={result.scaleScores} />
        </section>

        {interpretation ? (
          <section className="result-card">
            <h2 className="result-card-title">Интерпретация</h2>
            <pre className="result-text">{interpretation}</pre>
          </section>
        ) : null}

        {result.recommendations.length > 0 ? (
          <section className="result-card">
            <h2 className="result-card-title">Рекомендации</h2>
            <ol className="result-recs">
              {result.recommendations.map((rec, idx) => (
                <li key={idx}>{rec}</li>
              ))}
            </ol>
          </section>
        ) : null}

        <section className="result-card">
          <h2 className="result-card-title">Поделиться</h2>
          <div className="result-pinaba-block">
            <img
              src={pinabaSrc}
              alt="Pinaba — карточка с результатами"
              className="result-pinaba-image"
              loading="lazy"
            />
            <DownloadButtons sessionId={sessionId} shareUrl={shareUrl} />
          </div>
        </section>

        <p className="result-disclaimer">
          Этот отчёт носит ориентировочный характер и не является медицинским
          диагнозом.
        </p>
      </div>
    </main>
  )
}
