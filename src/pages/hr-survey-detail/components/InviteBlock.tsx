import { useState } from 'react'
import { Button } from '../../../shared/ui'

type Props = {
  inviteUrl: string
  disabled?: boolean
}

export default function InviteBlock({ inviteUrl, disabled }: Props) {
  const [copied, setCopied] = useState<'idle' | 'ok' | 'fail'>('idle')

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(inviteUrl)
      setCopied('ok')
      window.setTimeout(() => setCopied('idle'), 2000)
    } catch {
      setCopied('fail')
      window.setTimeout(() => setCopied('idle'), 2000)
    }
  }

  const label =
    copied === 'ok'
      ? 'Скопировано'
      : copied === 'fail'
        ? 'Не удалось'
        : 'Копировать ссылку'

  return (
    <section className="detail-card">
      <h2>Ссылка для приглашений</h2>
      <p className="detail-hint">
        Отправьте эту ссылку сотрудникам — они откроют опрос без регистрации.
        Каждый, кто откроет ссылку, получит уникальную сессию.
      </p>
      <div className="invite-row">
        <input
          type="text"
          className="invite-input"
          value={inviteUrl}
          readOnly
          onFocus={(event) => event.currentTarget.select()}
          aria-label="Ссылка для приглашений"
          data-testid="invite-input"
        />
        <Button
          type="button"
          variant="primary"
          onClick={() => void handleCopy()}
          disabled={disabled}
        >
          {label}
        </Button>
      </div>
    </section>
  )
}
