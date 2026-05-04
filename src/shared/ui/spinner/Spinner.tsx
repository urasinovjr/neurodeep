import './spinner.css'

type SpinnerSize = 'small' | 'medium' | 'large'

type SpinnerProps = {
  size?: SpinnerSize
  label?: string
}

export function Spinner({ size = 'medium', label = 'Загрузка…' }: SpinnerProps) {
  return (
    <span className={`ui-spinner ui-spinner--${size}`} role="status" aria-label={label}>
      <span className="ui-spinner__circle" />
    </span>
  )
}
