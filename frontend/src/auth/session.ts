/**
 * The browser-side session. In "dev" auth mode (the only mode so far) the
 * session is just the subject the developer signed in as, sent to the API
 * as the X-Dev-Subject header the backend's dev authenticator trusts. The
 * identity-provider mode will keep the same shape (a token instead of a
 * subject) behind the same functions.
 */

export type AuthMode = 'dev'

const STORAGE_KEY = 'greenhouse-insights.dev-subject'
const ORGANIZATION_KEY = 'greenhouse-insights.organization'

export function authMode(): AuthMode {
  const mode = import.meta.env.VITE_AUTH_MODE ?? 'dev'
  if (mode !== 'dev') {
    throw new Error(`unsupported VITE_AUTH_MODE ${JSON.stringify(mode)}`)
  }
  return mode
}

export function currentSubject(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

export function signIn(subject: string): void {
  window.localStorage.setItem(STORAGE_KEY, subject.trim())
}

export function signOut(): void {
  window.localStorage.removeItem(STORAGE_KEY)
}

export function authHeaders(): Record<string, string> {
  const subject = currentSubject()
  return subject ? { 'X-Dev-Subject': subject } : {}
}

export function selectedOrganization(): string | null {
  try {
    return window.localStorage.getItem(ORGANIZATION_KEY)
  } catch {
    return null
  }
}

export function rememberOrganization(organizationId: string | null): void {
  if (organizationId === null) {
    window.localStorage.removeItem(ORGANIZATION_KEY)
  } else {
    window.localStorage.setItem(ORGANIZATION_KEY, organizationId)
  }
}
