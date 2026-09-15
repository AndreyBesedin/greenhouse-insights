import type { ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { canAdminister, isPlatformAdmin } from '../auth/access'
import { useSession } from '../auth/SessionContext'
import { CropIcon } from './CropIcon'

function initials(label: string): string {
  const parts = label.split(/[\s@._-]+/).filter(Boolean)
  return parts
    .slice(0, 2)
    .map((part) => part[0]!.toUpperCase())
    .join('')
}

export function AppShell({ children }: { children: ReactNode }) {
  const { user, signOut, organizationId, selectOrganization } = useSession()
  const navigate = useNavigate()
  const label = user?.display_name ?? user?.email ?? null
  const organizations = user?.organizations ?? []
  const showSwitcher = organizations.length > 1
  const membersOrganizationId =
    organizationId ?? (organizations.length === 1 ? organizations[0]!.organization_id : null)
  return (
    <div className="min-h-screen bg-ink font-sans text-paper">
      <header className="border-b border-white/[0.06]">
        <div className="mx-auto flex h-14 max-w-[1440px] items-center gap-8 px-6">
          <Link to="/" className="flex items-center gap-2.5">
            <span className="grid size-7 place-items-center rounded-md bg-brand/15 text-brand outline-1 -outline-offset-1 outline-brand/30">
              <CropIcon crop="cherry-tomato" size="sm" />
            </span>
            <span className="font-display text-[15px] font-semibold tracking-tight">
              Greenhouse Insights
            </span>
          </Link>
          <nav className="hidden items-center gap-1 text-sm md:flex">
            <Link to="/" className="rounded-md px-3 py-1.5 font-medium text-paper">
              Greenhouses
            </Link>
            {membersOrganizationId !== null && canAdminister(user, membersOrganizationId) && (
              <Link
                to={`/organizations/${membersOrganizationId}/members`}
                className="rounded-md px-3 py-1.5 text-mist transition-colors hover:text-paper"
              >
                Members
              </Link>
            )}
            {isPlatformAdmin(user) && (
              <Link
                to="/admin"
                className="rounded-md px-3 py-1.5 text-mist transition-colors hover:text-paper"
              >
                Admin
              </Link>
            )}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            {showSwitcher && (
              <select
                aria-label="Organization"
                value={organizationId ?? ''}
                onChange={(event) => selectOrganization(event.target.value || null)}
                className="rounded-md bg-ink-800 px-2.5 py-1.5 text-xs text-paper outline-1 -outline-offset-1 outline-white/[0.07] focus:outline-brand/50"
              >
                <option value="">All organizations</option>
                {organizations.map((o) => (
                  <option key={o.organization_id} value={o.organization_id}>
                    {o.name}
                  </option>
                ))}
              </select>
            )}
            {label !== null && (
              <span className="hidden text-xs text-mist sm:inline" data-testid="current-user">
                {label}
                {user?.is_platform_admin && (
                  <span className="ml-2 rounded-sm bg-brand/10 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-brand outline-1 -outline-offset-1 outline-brand/30">
                    Platform admin
                  </span>
                )}
              </span>
            )}
            <button
              type="button"
              onClick={() => {
                signOut()
                navigate('/login')
              }}
              className="grid size-8 place-items-center rounded-full bg-ink-700 text-xs font-medium text-paper outline-1 -outline-offset-1 outline-white/10"
              title="Sign out"
              aria-label="Sign out"
            >
              {label !== null ? initials(label) : 'GI'}
            </button>
          </div>
        </div>
      </header>
      {children}
      <footer className="border-t border-white/[0.06]">
        <div className="mx-auto flex max-w-[1440px] items-center justify-between px-6 py-6 text-xs text-mist">
          <span>Greenhouse Insights</span>
          <span>Operator console</span>
        </div>
      </footer>
    </div>
  )
}
