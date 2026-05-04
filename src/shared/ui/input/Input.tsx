import { useId } from 'react'
import type { InputHTMLAttributes } from 'react'
import './input.css'

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label?: string
  error?: string
}

export function Input({ label, error, className, id, ...rest }: InputProps) {
  const generatedId = useId()
  const fieldId = id ?? generatedId
  const wrapClass = ['ui-input', error ? 'ui-input--error' : '', className ?? '']
    .filter(Boolean)
    .join(' ')
  return (
    <label className={wrapClass} htmlFor={fieldId}>
      {label && <span className="ui-input__label">{label}</span>}
      <input id={fieldId} className="ui-input__field" {...rest} />
      {error && <span className="ui-input__error">{error}</span>}
    </label>
  )
}
