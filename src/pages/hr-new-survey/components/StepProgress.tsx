import { TOTAL_STEPS } from '../hooks/useNewSurveyForm'

const STEP_LABELS = ['Название', 'Методика', 'Даты', 'Сообщение', 'Проверка']

type Props = {
  step: number
  onStepClick: (step: number) => void
}

export default function StepProgress({ step, onStepClick }: Props) {
  return (
    <ol className="new-survey-steps" aria-label="Шаги формы">
      {STEP_LABELS.map((label, idx) => {
        const stepNumber = idx + 1
        const isActive = stepNumber === step
        const isDone = stepNumber < step
        const cls = [
          'new-survey-step',
          isActive ? 'is-active' : '',
          isDone ? 'is-done' : '',
        ]
          .filter(Boolean)
          .join(' ')
        return (
          <li key={label} className={cls}>
            <button
              type="button"
              className="step-button"
              disabled={!isDone && !isActive}
              onClick={() => onStepClick(stepNumber)}
            >
              <span className="step-index">{stepNumber}</span>
              <span className="step-label">{label}</span>
            </button>
            {idx < TOTAL_STEPS - 1 ? <span className="step-divider" /> : null}
          </li>
        )
      })}
    </ol>
  )
}
