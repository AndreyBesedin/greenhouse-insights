import { describe, expect, it } from 'vitest'

import { canAdminister, canRead, canWrite, isPlatformAdmin, roleIn } from './access'
import { memberOf, PLATFORM_ADMIN } from '../test/session'

describe('access', () => {
  it('treats a signed-out visitor as able to do nothing', () => {
    expect(canRead(null, 'org_a')).toBe(false)
    expect(canWrite(null, 'org_a')).toBe(false)
    expect(canAdminister(null, 'org_a')).toBe(false)
    expect(isPlatformAdmin(null)).toBe(false)
  })

  it('lets a platform admin do everything everywhere', () => {
    expect(canRead(PLATFORM_ADMIN, 'org_unknown')).toBe(true)
    expect(canWrite(PLATFORM_ADMIN, 'org_unknown')).toBe(true)
    expect(canAdminister(PLATFORM_ADMIN, 'org_unknown')).toBe(true)
  })

  it('nests the organization roles', () => {
    const viewer = memberOf('VIEWER', 'org_a')
    const editor = memberOf('EDITOR', 'org_a')
    const admin = memberOf('ORGANIZATION_ADMIN', 'org_a')

    expect([
      canRead(viewer, 'org_a'),
      canWrite(viewer, 'org_a'),
      canAdminister(viewer, 'org_a'),
    ]).toEqual([true, false, false])
    expect([
      canRead(editor, 'org_a'),
      canWrite(editor, 'org_a'),
      canAdminister(editor, 'org_a'),
    ]).toEqual([true, true, false])
    expect([
      canRead(admin, 'org_a'),
      canWrite(admin, 'org_a'),
      canAdminister(admin, 'org_a'),
    ]).toEqual([true, true, true])
  })

  it('grants nothing in another organization', () => {
    const admin = memberOf('ORGANIZATION_ADMIN', 'org_a')

    expect(roleIn(admin, 'org_b')).toBeNull()
    expect(canRead(admin, 'org_b')).toBe(false)
  })
})
