import './logo.css'

type LogoProps = {
  size?: 'small' | 'medium' | 'large'
  className?: string
}

export function Logo({ size = 'medium', className }: LogoProps) {
  const classes = ['ui-logo', `ui-logo--${size}`, className ?? ''].filter(Boolean).join(' ')
  return (
    <span className={classes}>
      <span className="ui-logo__mark" aria-hidden>Ψ</span>
      <span className="ui-logo__text">PsychoGraph</span>
    </span>
  )
}
