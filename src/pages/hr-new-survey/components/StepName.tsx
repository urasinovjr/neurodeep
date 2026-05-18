import { Input } from '../../../shared/ui'
import { NAME_MAX } from '../hooks/useNewSurveyForm'

type Props = {
  value: string
  error: string | undefined
  onChange: (value: string) => void
}

export default function StepName({ value, error, onChange }: Props) {
  return (
    <section className="new-survey-step-body">
      <h2>Название исследования</h2>
      <p className="step-hint">
        Видно только вам и админам. Респонденты не увидят это название.
      </p>
      <Input
        label="Название"
        value={value}
        error={error}
        maxLength={NAME_MAX}
        placeholder="Например: «Q2 — диагностика тревожности в инженерном отделе»"
        onChange={(event) => onChange(event.target.value)}
        autoFocus
      />
      <p className="step-counter">
        {value.length} / {NAME_MAX}
      </p>
    </section>
  )
}
