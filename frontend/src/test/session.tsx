import type { ReactNode } from 'react'

import { SessionContext, type CurrentUser, type SessionState } from '../auth/SessionContext'

export const PLATFORM_ADMIN: CurrentUser = {
  user_id: 'user_root',
  email: 'dev-admin@dev.local',
  display_name: 'dev-admin',
  is_platform_admin: true,
  organizations: [
    {
      organization_id: 'org_serrapulse_internal',
      name: 'SerraPulse Internal',
      slug: 'serrapulse-internal',
      role: null,
    },
  ],
}

export function memberOf(
  role: 'VIEWER' | 'EDITOR' | 'ORGANIZATION_ADMIN',
  organizationId = 'org_serrapulse_internal',
): CurrentUser {
  return {
    user_id: `user_${role.toLowerCase()}`,
    email: `${role.toLowerCase()}@dev.local`,
    display_name: null,
    is_platform_admin: false,
    organizations: [
      { organization_id: organizationId, name: organizationId, slug: organizationId, role },
    ],
  }
}

/** Wraps `ui` in a session for `user` (a platform admin by default). */
export function withSession(
  ui: ReactNode,
  user: CurrentUser | null = PLATFORM_ADMIN,
  overrides: Partial<SessionState> = {},
) {
  const state: SessionState = {
    subject: user ? 'dev' : null,
    user,
    loading: false,
    initializing: false,
    organizationId: null,
    selectOrganization: () => {},
    signIn: () => {},
    signOut: () => {},
    ...overrides,
  }
  return <SessionContext.Provider value={state}>{ui}</SessionContext.Provider>
}
