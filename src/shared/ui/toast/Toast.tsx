import { useEffect } from 'react'
import './toast.css'

type ToastVariant = 'success' | 'warn' | 'danger' | 'info'

type ToastProps = {
  message: string
  variant?: ToastVariant
  durationMs?: number
  onClose?: () => void
}

export function Toast({ message, variant = 'info', durationMs = 4000, onClose }: ToastProps) {
  useEffect(() => {
    if (!onClose || durationMs <= 0) return
    const timer = window.setTimeout(onClose, durationMs)
    return () => window.clearTimeout(timer)
  }, [onClose, durationMs])

  return (
    <div className={`ui-toast ui-toast--${variant}`} role="status" aria-live="polite">
      <span className="ui-toast__message">{message}</span>
      {onClose && (
        <button
          type="button"
          className="ui-toast__close"
          aria-label="Закрыть"
          onClick={onClose}
        >
          ×
        </button>
      )}
    </div>
  )
}
