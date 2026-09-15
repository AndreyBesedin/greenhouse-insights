import { useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'

import { apiClient } from '../api/client'
import { canAdminister, ROLE_LABEL, type OrganizationRole } from '../auth/access'
import { useSession } from '../auth/SessionContext'
import { AppShell } from '../components/AppShell'
import type { components } from '../../generated/schema'

type Member = components['schemas']['Member']

const ROLE_OPTIONS: OrganizationRole[] = ['VIEWER', 'EDITOR', 'ORGANIZATION_ADMIN']

const SELECT_CLS =
  'rounded-md bg-ink-800 px-2.5 py-1.5 text-xs text-paper outline-1 -outline-offset-1 outline-white/[0.07] focus:outline-brand/50'

export function OrganizationMembersPage() {
  const { organizationId } = useParams<{ organizationId: string }>()
  const { user } = useSession()
  const organization = user?.organizations.find((o) => o.organization_id === organizationId)
  const [members, setMembers] = useState<Member[] | null>(null)
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<OrganizationRole>('VIEWER')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!organizationId) return
    let cancelled = false
    apiClient
      .GET('/organizations/{organization_id}/members', {
        params: { path: { organization_id: organizationId } },
      })
      .then(({ data }) => {
        if (!cancelled) setMembers(data ?? [])
      })
    return () => {
      cancelled = true
    }
  }, [organizationId])

  async function setMember(memberEmail: string, memberRole: OrganizationRole) {
    if (!organizationId) return
    setBusy(true)
    setError(null)
    const {
      data,
      error: apiError,
      response,
    } = await apiClient.PUT('/organizations/{organization_id}/members', {
      params: { path: { organization_id: organizationId } },
      body: { email: memberEmail, role: memberRole },
    })
    setBusy(false)
    if (apiError || !data) {
      setError(
        response.status === 404
          ? 'No user with that email has signed in yet. Ask them to sign in once first.'
          : 'Could not save that membership. Try again.',
      )
      return
    }
    setMembers((current) => [...(current ?? []).filter((m) => m.user_id !== data.user_id), data])
    setEmail('')
  }

  async function removeMember(member: Member) {
    if (!organizationId) return
    setBusy(true)
    setError(null)
    const { error: apiError } = await apiClient.DELETE(
      '/organizations/{organization_id}/members/{user_id}',
      { params: { path: { organization_id: organizationId, user_id: member.user_id } } },
    )
    setBusy(false)
    if (apiError) {
      setError('Could not remove that member. Try again.')
      return
    }
    setMembers((current) => (current ?? []).filter((m) => m.user_id !== member.user_id))
  }

  function onAdd(event: FormEvent) {
    event.preventDefault()
    if (email.trim()) void setMember(email.trim(), role)
  }

  if (organizationId && !canAdminister(user, organizationId) && user !== null) {
    return (
      <AppShell>
        <main className="mx-auto max-w-[1440px] px-6 py-10">
          <p className="text-sm text-mist">Only organization admins can manage members.</p>
        </main>
      </AppShell>
    )
  }

  return (
    <AppShell>
      <main className="mx-auto max-w-[1440px] px-6 py-10">
        <div className="mb-6 text-xs text-mist">
          <Link to="/" className="transition-colors hover:text-paper">
            ← Greenhouses
          </Link>
        </div>
        <h1 className="font-display text-xl font-medium tracking-tight">
          {organization?.name ?? organizationId} · Members
        </h1>
        <p className="mt-1 mb-6 text-sm text-mist">
          Viewers browse, editors operate greenhouses, organization admins also manage members.
        </p>

        <form
          onSubmit={onAdd}
          className="mb-6 flex flex-wrap items-end gap-3 rounded-lg bg-ink-850 p-5 outline-1 -outline-offset-1 outline-white/[0.06]"
        >
          <div className="grow">
            <label htmlFor="member-email" className="mb-1.5 block text-xs text-mist">
              Email of a user who has signed in
            </label>
            <input
              id="member-email"
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="w-full rounded-md bg-ink-800 px-3.5 py-2.5 text-sm text-paper outline-1 -outline-offset-1 outline-white/[0.07] focus:outline-brand/50"
            />
          </div>
          <div>
            <label htmlFor="member-role" className="mb-1.5 block text-xs text-mist">
              Role
            </label>
            <select
              id="member-role"
              value={role}
              onChange={(event) => setRole(event.target.value as OrganizationRole)}
              className={SELECT_CLS + ' py-2.5 text-sm'}
            >
              {ROLE_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {ROLE_LABEL[option]}
                </option>
              ))}
            </select>
          </div>
          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-brand px-3.5 py-2.5 text-sm font-medium text-ink transition-colors hover:bg-brand/90 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Add member
          </button>
        </form>

        {error && <p className="mb-4 text-xs text-terra">{error}</p>}

        {members === null ? (
          <p className="text-sm text-mist">Loading members…</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-mist">
                <th className="py-2 font-normal">Member</th>
                <th className="py-2 font-normal">Role</th>
                <th className="py-2" />
              </tr>
            </thead>
            <tbody>
              {members.map((member) => (
                <tr key={member.user_id} className="border-t border-white/[0.06]">
                  <td className="py-2.5">
                    <div>{member.display_name ?? member.email}</div>
                    {member.display_name !== null && (
                      <div className="text-xs text-mist">{member.email}</div>
                    )}
                  </td>
                  <td className="py-2.5">
                    <select
                      aria-label={`Role of ${member.email}`}
                      value={member.role}
                      disabled={busy}
                      onChange={(event) =>
                        void setMember(member.email, event.target.value as OrganizationRole)
                      }
                      className={SELECT_CLS}
                    >
                      {ROLE_OPTIONS.map((option) => (
                        <option key={option} value={option}>
                          {ROLE_LABEL[option]}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="py-2.5 text-right">
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => void removeMember(member)}
                      className="rounded-md px-2 py-1 text-xs text-mist transition-colors hover:text-terra disabled:opacity-40"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </main>
    </AppShell>
  )
}
