import { useState } from 'react'
import { Button } from '../../../shared/ui'
import {
  downloadPdfUrl,
  downloadPinabaUrl,
} from '../api/respondentApi'

type Props = {
  sessionId: string
  shareUrl: string
}

export default function DownloadButtons({ sessionId, shareUrl }: Props) {
  const [copyStatus, setCopyStatus] = useState<'idle' | 'copied' | 'failed'>(
    'idle',
  )

  const handleShare = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl)
      setCopyStatus('copied')
      window.setTimeout(() => setCopyStatus('idle'), 2000)
    } catch {
      setCopyStatus('failed')
      window.setTimeout(() => setCopyStatus('idle'), 2000)
    }
  }

  const copyLabel =
    copyStatus === 'copied'
      ? 'Ссылка скопирована'
      : copyStatus === 'failed'
        ? 'Не удалось скопировать'
        : 'Поделиться анонимной ссылкой'

  return (
    <div className="result-downloads" data-testid="result-downloads">
      <a
        className="result-download-button result-download-primary"
        href={downloadPdfUrl(sessionId)}
        download={`psychograph-${sessionId}.pdf`}
      >
        Скачать PDF
      </a>
      <a
        className="result-download-button"
        href={downloadPinabaUrl(sessionId)}
        download={`psychograph-${sessionId}.png`}
      >
        Скачать pinaba PNG
      </a>
      <Button
        type="button"
        variant="secondary"
        onClick={() => void handleShare()}
      >
        {copyLabel}
      </Button>
    </div>
  )
}
