export type FormatDateOptions = {
  withTime?: boolean
  fallback?: string
}

export function formatDate(
  value: string | null | undefined,
  options: FormatDateOptions = {},
): string {
  const fallback = options.fallback ?? '—'
  if (!value) return fallback
  try {
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return fallback
    const formatOptions: Intl.DateTimeFormatOptions = {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    }
    if (options.withTime) {
      formatOptions.hour = '2-digit'
      formatOptions.minute = '2-digit'
    }
    return new Intl.DateTimeFormat('ru-RU', formatOptions).format(date)
  } catch {
    return fallback
  }
}
