import { Textarea } from '../../../shared/ui'
import { WELCOME_MAX } from '../hooks/useNewSurveyForm'

type Props = {
  welcomeMessage: string
  allowIndividualShare: boolean
  welcomeError: string | undefined
  onMessage: (value: string) => void
  onAllowShare: (value: boolean) => void
}

export default function StepWelcome({
  welcomeMessage,
  allowIndividualShare,
  welcomeError,
  onMessage,
  onAllowShare,
}: Props) {
  return (
    <section className="new-survey-step-body">
      <h2>Приветствие и согласие</h2>
      <p className="step-hint">
        Сообщение видит респондент на старте опроса. Чек-бокс ниже разрешает
        делиться индивидуальными результатами (по умолчанию — только агрегаты для
        HR).
      </p>
      <Textarea
        label="Приветственное сообщение"
        value={welcomeMessage}
        error={welcomeError}
        maxLength={WELCOME_MAX}
        rows={6}
        placeholder="Например: «Привет! Это короткая диагностика — поможет нам понять, где команда чувствует себя устойчиво, а где можно подставить плечо.»"
        onChange={(event) => onMessage(event.target.value)}
      />
      <p className="step-counter">
        {welcomeMessage.length} / {WELCOME_MAX}
      </p>
      <label className="step-checkbox">
        <input
          type="checkbox"
          checked={allowIndividualShare}
          onChange={(event) => onAllowShare(event.target.checked)}
        />
        <span>
          Разрешить делиться индивидуальными результатами (респондент сможет
          поделиться своим профилем с HR)
        </span>
      </label>
    </section>
  )
}
