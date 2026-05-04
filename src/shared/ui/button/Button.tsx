import type { ButtonHTMLAttributes, ReactNode } from 'react'
import './button.css'

type ButtonVariant = 'primary' | 'secondary' | 'danger'
type ButtonSize = 'medium' | 'large'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant
  size?: ButtonSize
  isLoading?: boolean
  children: ReactNode
}

export function Button({
  variant = 'primary',
  size = 'medium',
  isLoading = false,
  disabled,
  children,
  className,
  type = 'button',
  ...rest
}: ButtonProps) {
  const classes = [
    'ui-button',
    `ui-button--${variant}`,
    `ui-button--${size}`,
    isLoading ? 'ui-button--loading' : '',
    className ?? '',
  ]
    .filter(Boolean)
    .join(' ')
  return (
    <button
      type={type}
      className={classes}
      disabled={disabled || isLoading}
      {...rest}
    >
      {children}
    </button>
  )
}
