import { describe, expect, it, vi } from 'vitest'
import type { Auth0Client } from '@auth0/auth0-spa-js'

import { createOidcSession, type OidcConfig } from './oidc'

const CONFIG: OidcConfig = { domain: 'tenant.example', clientId: 'cid', audience: 'https://api' }

function fakeClient(overrides: Partial<Auth0Client> = {}) {
  const client = {
    handleRedirectCallback: vi.fn().mockResolvedValue({ appState: { returnTo: '/greenhouses/x' } }),
    isAuthenticated: vi.fn().mockResolvedValue(true),
    getUser: vi.fn().mockResolvedValue({ sub: 'auth0|abc' }),
    loginWithRedirect: vi.fn().mockResolvedValue(undefined),
    logout: vi.fn().mockResolvedValue(undefined),
    getTokenSilently: vi.fn().mockResolvedValue('token-123'),
    ...overrides,
  }
  return client as unknown as Auth0Client & typeof client
}

describe('oidc session', () => {
  it('creates the provider client once, on first use', async () => {
    const client = fakeClient()
    const create = vi.fn().mockResolvedValue(client)
    const session = createOidcSession(CONFIG, create)

    await session.token()
    await session.bootstrap()

    expect(create).toHaveBeenCalledTimes(1)
    expect(create).toHaveBeenCalledWith(CONFIG)
  })

  it('reports the subject when a session exists', async () => {
    const session = createOidcSession(CONFIG, async () => fakeClient())

    expect(await session.bootstrap()).toBe('auth0|abc')
  })

  it('reports nobody when signed out', async () => {
    const session = createOidcSession(CONFIG, async () =>
      fakeClient({ isAuthenticated: vi.fn().mockResolvedValue(false) }),
    )

    expect(await session.bootstrap()).toBeNull()
  })

  it('finishes a login redirect and restores the requested route', async () => {
    const client = fakeClient()
    window.history.pushState({}, '', '/?code=abc&state=xyz')
    const session = createOidcSession(CONFIG, async () => client)

    await session.bootstrap()

    expect(client.handleRedirectCallback).toHaveBeenCalled()
    expect(window.location.pathname).toBe('/greenhouses/x')
    expect(window.location.search).toBe('')
  })

  it('sends the API a bearer token, or nothing when the provider has none', async () => {
    const withToken = createOidcSession(CONFIG, async () => fakeClient())
    const without = createOidcSession(CONFIG, async () =>
      fakeClient({ getTokenSilently: vi.fn().mockRejectedValue(new Error('login_required')) }),
    )

    expect(await withToken.token()).toBe('token-123')
    expect(await without.token()).toBeNull()
  })

  it('logs in with the route to return to and logs out back to the login page', async () => {
    const client = fakeClient()
    const session = createOidcSession(CONFIG, async () => client)

    await session.login('/greenhouses/x')
    await session.logout()

    expect(client.loginWithRedirect).toHaveBeenCalledWith({
      appState: { returnTo: '/greenhouses/x' },
    })
    expect(client.logout).toHaveBeenCalledWith({
      logoutParams: { returnTo: `${window.location.origin}/login` },
    })
  })
})
