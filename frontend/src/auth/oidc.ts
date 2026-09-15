/**
 * The identity-provider session: Auth0's SPA SDK (authorization code +
 * PKCE, tokens kept in memory). Wrapped in a small interface so the rest
 * of the app - and its tests - never touch the SDK directly.
 */

import { createAuth0Client, type Auth0Client } from '@auth0/auth0-spa-js'

export type OidcConfig = {
  domain: string
  clientId: string
  audience: string
}

export type OidcSession = {
  /** Finishes a login redirect if one is in progress and reports the
   * signed-in subject, or null when nobody is signed in. */
  bootstrap: () => Promise<string | null>
  login: (returnTo: string) => Promise<void>
  logout: () => Promise<void>
  /** A fresh access token for the API, or null when signed out. */
  token: () => Promise<string | null>
}

export function oidcConfigFromEnv(): OidcConfig {
  const domain = import.meta.env.VITE_OIDC_DOMAIN ?? ''
  const clientId = import.meta.env.VITE_OIDC_CLIENT_ID ?? ''
  const audience = import.meta.env.VITE_OIDC_AUDIENCE ?? ''
  const missing = [
    ['VITE_OIDC_DOMAIN', domain],
    ['VITE_OIDC_CLIENT_ID', clientId],
    ['VITE_OIDC_AUDIENCE', audience],
  ]
    .filter(([, value]) => !value)
    .map(([name]) => name)
  if (missing.length > 0) {
    throw new Error(`VITE_AUTH_MODE=oidc requires ${missing.join(', ')}`)
  }
  return { domain, clientId, audience }
}

export function createOidcSession(
  config: OidcConfig,
  createClient: (config: OidcConfig) => Promise<Auth0Client> = defaultCreateClient,
): OidcSession {
  let clientPromise: Promise<Auth0Client> | null = null
  const client = () => (clientPromise ??= createClient(config))

  return {
    async bootstrap() {
      const auth0 = await client()
      const params = new URLSearchParams(window.location.search)
      if (params.has('code') && params.has('state')) {
        const { appState } = await auth0.handleRedirectCallback<{ returnTo?: string }>()
        window.history.replaceState({}, '', appState?.returnTo ?? '/')
      }
      if (!(await auth0.isAuthenticated())) {
        return null
      }
      const user = await auth0.getUser()
      return user?.sub ?? null
    },
    async login(returnTo) {
      const auth0 = await client()
      await auth0.loginWithRedirect({ appState: { returnTo } })
    },
    async logout() {
      const auth0 = await client()
      await auth0.logout({ logoutParams: { returnTo: `${window.location.origin}/login` } })
    },
    async token() {
      const auth0 = await client()
      try {
        return (await auth0.getTokenSilently()) ?? null
      } catch {
        return null
      }
    },
  }
}

function defaultCreateClient(config: OidcConfig): Promise<Auth0Client> {
  return createAuth0Client({
    domain: config.domain,
    clientId: config.clientId,
    authorizationParams: {
      audience: config.audience,
      redirect_uri: window.location.origin,
      scope: 'openid profile email',
    },
    // Keep the session across reloads without third-party cookies.
    cacheLocation: 'localstorage',
    useRefreshTokens: true,
  })
}
