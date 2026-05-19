const STORAGE_KEY_PREFIX = 'psychograph_session_'
const LEGACY_KEY = 'psychograph_session_id'

export type SessionRestore = {
  sessionId: string
  lastKnownIndex: number
}

function storageKeyFor(inviteToken: string): string {
  return `${STORAGE_KEY_PREFIX}${inviteToken}`
}

function isValidRestore(value: unknown): value is SessionRestore {
  if (typeof value !== 'object' || value === null) return false
  const record = value as Record<string, unknown>
  return (
    typeof record.sessionId === 'string' &&
    record.sessionId.length > 0 &&
    typeof record.lastKnownIndex === 'number' &&
    Number.isFinite(record.lastKnownIndex)
  )
}

export function readSessionRestore(inviteToken: string): SessionRestore | null {
  try {
    const raw = window.localStorage.getItem(storageKeyFor(inviteToken))
    if (!raw) return null
    const parsed: unknown = JSON.parse(raw)
    if (!isValidRestore(parsed)) {
      window.localStorage.removeItem(storageKeyFor(inviteToken))
      return null
    }
    return parsed
  } catch {
    return null
  }
}

export function writeSessionRestore(
  inviteToken: string,
  payload: SessionRestore,
): void {
  try {
    window.localStorage.setItem(
      storageKeyFor(inviteToken),
      JSON.stringify(payload),
    )
  } catch {}
}

export function clearSessionRestore(inviteToken: string): void {
  try {
    window.localStorage.removeItem(storageKeyFor(inviteToken))
  } catch {}
}

export function clearLegacySessionKey(): void {
  try {
    window.localStorage.removeItem(LEGACY_KEY)
  } catch {}
}
