/**
 * The browser-side session, in one of two modes:
 *
 * - "dev": the subject the developer signed in as, sent to the API as the
 *   X-Dev-Subject header the backend's dev authenticator trusts;
 * - "oidc": an identity-provider login (see ./oidc.ts) whose access token
 *   is sent as a bearer token.
 *
 * Both expose the same functions, so the provider and the API client do
 * not care which is active.
 */

import { createOidcSession, oidcConfigFromEnv, type OidcSession } from './oidc'

export type AuthMode = 'dev' | 'oidc'

const STORAGE_KEY = 'greenhouse-insights.dev-subject'
const ORGANIZATION_KEY = 'greenhouse-insights.organization'

export function authMode(): AuthMode {
  const mode = import.meta.env.VITE_AUTH_MODE ?? 'dev'
  if (mode !== 'dev' && mode !== 'oidc') {
    throw new Error(`unsupported VITE_AUTH_MODE ${JSON.stringify(mode)}`)
  }
  return mode
}

let oidcSession: OidcSession | null = null

/** The identity-provider session; created on first use in oidc mode. */
export function oidc(): OidcSession {
  return (oidcSession ??= createOidcSession(oidcConfigFromEnv()))
}

/** Test seam: replace the identity-provider session. */
export function useOidcSession(session: OidcSession | null): void {
  oidcSession = session
}

// -- dev mode ---------------------------------------------------------------

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

// -- both modes -------------------------------------------------------------

/** The credential headers for an API request; empty when signed out. */
export async function authHeaders(): Promise<Record<string, string>> {
  if (authMode() === 'oidc') {
    const token = await oidc().token()
    return token ? { Authorization: `Bearer ${token}` } : {}
  }
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
