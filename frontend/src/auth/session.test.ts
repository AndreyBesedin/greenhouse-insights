import { beforeEach, describe, expect, it } from 'vitest'

import { authHeaders, authMode, currentSubject, signIn, signOut } from './session'

beforeEach(() => signOut())

describe('dev session', () => {
  it('has no subject and sends no credential when signed out', async () => {
    expect(currentSubject()).toBeNull()
    expect(await authHeaders()).toEqual({})
  })

  it('sends the signed-in subject as the dev header', async () => {
    signIn('  dev-alice ')

    expect(currentSubject()).toBe('dev-alice')
    expect(await authHeaders()).toEqual({ 'X-Dev-Subject': 'dev-alice' })
  })

  it('forgets the subject on sign out', () => {
    signIn('dev-alice')
    signOut()

    expect(currentSubject()).toBeNull()
  })

  it('runs in dev mode unless VITE_AUTH_MODE says otherwise', () => {
    expect(authMode()).toBe('dev')
  })
})
