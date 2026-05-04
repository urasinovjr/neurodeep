import { useId } from 'react'
import type { TextareaHTMLAttributes } from 'react'
import './textarea.css'

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label?: string
  error?: string
}

export function Textarea({ label, error, className, id, rows = 4, ...rest }: TextareaProps) {
  const generatedId = useId()
  const fieldId = id ?? generatedId
  const wrapClass = ['ui-textarea', error ? 'ui-textarea--error' : '', className ?? '']
    .filter(Boolean)
    .join(' ')
  return (
    <label className={wrapClass} htmlFor={fieldId}>
      {label && <span className="ui-textarea__label">{label}</span>}
      <textarea id={fieldId} rows={rows} className="ui-textarea__field" {...rest} />
      {error && <span className="ui-textarea__error">{error}</span>}
    </label>
  )
}
