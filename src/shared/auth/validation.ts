const PASSWORD_SPECIAL_CHARS = '!@#$%^&*()_-+=[]{};:,.<>/?|`'
const PASSWORD_SPECIAL_REGEX = /[!@#$%^&*()_\-+=[\]{};:,.<>/?|`]/
const PASSWORD_UPPER_REGEX = /[A-ZА-ЯЁ]/
const PASSWORD_DIGIT_REGEX = /\d/
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export const PASSWORD_RULES_HINT =
  `8–128 символов, минимум одна заглавная буква, одна цифра и один спецсимвол (${PASSWORD_SPECIAL_CHARS})`

export function validateEmail(value: string): string | null {
  if (!value.trim()) return 'Введите email'
  if (!EMAIL_REGEX.test(value.trim())) return 'Некорректный email'
  return null
}

export function validatePassword(value: string): string | null {
  if (value.length < 8 || value.length > 128) return 'Пароль должен быть от 8 до 128 символов'
  if (!PASSWORD_UPPER_REGEX.test(value)) return 'Пароль должен содержать минимум одну заглавную букву'
  if (!PASSWORD_DIGIT_REGEX.test(value)) return 'Пароль должен содержать минимум одну цифру'
  if (!PASSWORD_SPECIAL_REGEX.test(value)) return 'Пароль должен содержать минимум один спецсимвол'
  return null
}

export function validateRequired(value: string, fieldLabel: string): string | null {
  if (!value.trim()) return `Поле «${fieldLabel}» обязательно`
  if (value.trim().length > 100) return `Поле «${fieldLabel}» слишком длинное (макс 100)`
  return null
}
