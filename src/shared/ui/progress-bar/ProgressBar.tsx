import './progress-bar.css'

type ProgressBarProps = {
  value: number
  max?: number
  label?: string
}

export function ProgressBar({ value, max = 100, label }: ProgressBarProps) {
  const safeMax = max <= 0 ? 100 : max
  const clamped = Math.max(0, Math.min(value, safeMax))
  const percent = (clamped / safeMax) * 100
  return (
    <div className="ui-progress-bar">
      {label && <div className="ui-progress-bar__label">{label}</div>}
      <div
        className="ui-progress-bar__track"
        role="progressbar"
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={safeMax}
      >
        <div className="ui-progress-bar__fill" style={{ width: `${percent}%` }} />
      </div>
      <div className="ui-progress-bar__caption">
        {Math.round(percent)}%
      </div>
    </div>
  )
}
