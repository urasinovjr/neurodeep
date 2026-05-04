import './logo.css'

type LogoProps = {
  size?: 'small' | 'medium' | 'large'
}

export function Logo({ size = 'medium' }: LogoProps) {
  return (
    <span className={`ui-logo ui-logo--${size}`}>
      <span className="ui-logo__mark" aria-hidden>Ψ</span>
      <span className="ui-logo__text">PsychoGraph</span>
    </span>
  )
}
