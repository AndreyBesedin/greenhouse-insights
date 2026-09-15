/**
 * What the signed-in user may do, derived from GET /me. UX only: every
 * control hidden here is also refused by the backend for that actor.
 */

import type { CurrentUser } from './SessionContext'
import type { components } from '../../generated/schema'

export type OrganizationRole = components['schemas']['OrganizationRole']

export function isPlatformAdmin(user: CurrentUser | null): boolean {
  return user?.is_platform_admin ?? false
}

export function roleIn(user: CurrentUser | null, organizationId: string): OrganizationRole | null {
  return user?.organizations.find((o) => o.organization_id === organizationId)?.role ?? null
}

/** Read access: any membership, or platform admin. */
export function canRead(user: CurrentUser | null, organizationId: string): boolean {
  return isPlatformAdmin(user) || roleIn(user, organizationId) !== null
}

/** Operate: advance days, review recommendations, submit manual actions. */
export function canWrite(user: CurrentUser | null, organizationId: string): boolean {
  if (isPlatformAdmin(user)) return true
  const role = roleIn(user, organizationId)
  return role === 'EDITOR' || role === 'ORGANIZATION_ADMIN'
}

/** Manage the organization's members. */
export function canAdminister(user: CurrentUser | null, organizationId: string): boolean {
  return isPlatformAdmin(user) || roleIn(user, organizationId) === 'ORGANIZATION_ADMIN'
}

export const ROLE_LABEL: Record<OrganizationRole, string> = {
  VIEWER: 'Viewer',
  EDITOR: 'Editor',
  ORGANIZATION_ADMIN: 'Organization admin',
}
