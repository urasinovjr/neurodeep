import { useEffect, useRef, useState } from 'react'
import QRCode from 'qrcode'
import { Button } from '../../../shared/ui'

type Props = {
  inviteUrl: string
  filename: string
}

export default function QrBlock({ inviteUrl, filename }: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function render(): Promise<void> {
      if (!canvasRef.current) return
      try {
        await QRCode.toCanvas(canvasRef.current, inviteUrl, {
          errorCorrectionLevel: 'M',
          margin: 2,
          width: 240,
          color: { dark: '#0F172A', light: '#FFFFFF' },
        })
        if (!cancelled) setError(null)
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Не удалось сгенерировать QR.')
        }
      }
    }
    void render()
    return () => {
      cancelled = true
    }
  }, [inviteUrl])

  const handleDownload = async () => {
    try {
      const dataUrl = await QRCode.toDataURL(inviteUrl, {
        errorCorrectionLevel: 'M',
        margin: 2,
        width: 1080,
        color: { dark: '#0F172A', light: '#FFFFFF' },
      })
      const link = document.createElement('a')
      link.href = dataUrl
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    } catch {
      setError('Не удалось скачать QR.')
    }
  }

  return (
    <section className="detail-card">
      <h2>QR-код для печати</h2>
      <p className="detail-hint">
        Распечатайте QR для оффлайн-приглашения: на флайере, в офисе, в письме.
        Скан ведёт на ту же ссылку, что и кнопка «Копировать».
      </p>
      <div className="qr-row">
        <canvas
          ref={canvasRef}
          className="qr-canvas"
          width={240}
          height={240}
          aria-label="QR-код ссылки для приглашений"
          data-testid="qr-canvas"
        />
        <Button
          type="button"
          variant="secondary"
          onClick={() => void handleDownload()}
        >
          Скачать QR
        </Button>
      </div>
      {error ? <p className="detail-error">{error}</p> : null}
    </section>
  )
}
