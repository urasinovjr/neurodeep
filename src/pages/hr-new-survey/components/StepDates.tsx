import { Input } from '../../../shared/ui'

type Props = {
  startDate: string
  endDate: string
  endError: string | undefined
  onStart: (value: string) => void
  onEnd: (value: string) => void
}

export default function StepDates({
  startDate,
  endDate,
  endError,
  onStart,
  onEnd,
}: Props) {
  return (
    <section className="new-survey-step-body">
      <h2>Период проведения</h2>
      <p className="step-hint">
        Поля необязательные. Если оставите пустыми — респонденты смогут пройти
        опрос в любое время после активации.
      </p>
      <div className="step-row">
        <Input
          type="datetime-local"
          label="Старт"
          value={startDate}
          onChange={(event) => onStart(event.target.value)}
        />
        <Input
          type="datetime-local"
          label="Окончание"
          value={endDate}
          error={endError}
          onChange={(event) => onEnd(event.target.value)}
        />
      </div>
    </section>
  )
}
