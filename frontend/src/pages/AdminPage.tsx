import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'

import { apiClient } from '../api/client'
import { isPlatformAdmin } from '../auth/access'
import { useSession } from '../auth/SessionContext'
import { AppShell } from '../components/AppShell'
import type { components } from '../../generated/schema'

type OrganizationAccess = components['schemas']['OrganizationAccess']
type UserSummary = components['schemas']['UserSummary']

const INPUT_CLS =
  'w-full rounded-md bg-ink-800 px-3.5 py-2.5 text-sm text-paper outline-1 -outline-offset-1 outline-white/[0.07] focus:outline-brand/50'

export function AdminPage() {
  const { user } = useSession()
  const [organizations, setOrganizations] = useState<OrganizationAccess[] | null>(null)
  const [users, setUsers] = useState<UserSummary[] | null>(null)
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    apiClient.GET('/organizations').then(({ data }) => {
      if (!cancelled) setOrganizations(data ?? [])
    })
    apiClient.GET('/admin/users').then(({ data }) => {
      if (!cancelled) setUsers(data ?? [])
    })
    return () => {
      cancelled = true
    }
  }, [])

  async function onCreateOrganization(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    const {
      data,
      error: apiError,
      response,
    } = await apiClient.POST('/organizations', {
      body: { name: name.trim(), slug: slug.trim() },
    })
    setBusy(false)
    if (apiError || !data) {
      setError(
        response.status === 409
          ? 'That slug is already taken.'
          : 'Could not create the organization. Slugs are lowercase letters, digits and dashes.',
      )
      return
    }
    setOrganizations((current) => [
      ...(current ?? []),
      { organization_id: data.organization_id, name: data.name, slug: data.slug, role: null },
    ])
    setName('')
    setSlug('')
  }

  async function setPlatformAdmin(target: UserSummary, isAdmin: boolean) {
    setBusy(true)
    setError(null)
    const { data, error: apiError } = await apiClient.PUT('/admin/users/{user_id}/platform-admin', {
      params: { path: { user_id: target.user_id } },
      body: { is_platform_admin: isAdmin },
    })
    setBusy(false)
    if (apiError || !data) {
      setError('Could not change that user. Try again.')
      return
    }
    setUsers((current) => (current ?? []).map((u) => (u.user_id === data.user_id ? data : u)))
  }

  if (user !== null && !isPlatformAdmin(user)) {
    return (
      <AppShell>
        <main className="mx-auto max-w-[1440px] px-6 py-10">
          <p className="text-sm text-mist">Only platform admins can open this page.</p>
        </main>
      </AppShell>
    )
  }

  return (
    <AppShell>
      <main className="mx-auto max-w-[1440px] px-6 py-10">
        <h1 className="mb-6 font-display text-xl font-medium tracking-tight">
          Platform administration
        </h1>

        {error && <p className="mb-4 text-xs text-terra">{error}</p>}

        <div className="grid gap-6 lg:grid-cols-2">
          <section className="rounded-lg bg-ink-850 p-5 outline-1 -outline-offset-1 outline-white/[0.06]">
            <h2 className="font-display text-sm font-medium">Organizations</h2>
            <form
              onSubmit={onCreateOrganization}
              className="mt-4 mb-5 grid gap-3 sm:grid-cols-[1fr_1fr_auto]"
            >
              <div>
                <label htmlFor="org-name" className="mb-1.5 block text-xs text-mist">
                  Name
                </label>
                <input
                  id="org-name"
                  required
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  className={INPUT_CLS}
                />
              </div>
              <div>
                <label htmlFor="org-slug" className="mb-1.5 block text-xs text-mist">
                  Slug
                </label>
                <input
                  id="org-slug"
                  required
                  pattern="[a-z0-9]+(-[a-z0-9]+)*"
                  value={slug}
                  onChange={(event) => setSlug(event.target.value)}
                  className={INPUT_CLS}
                />
              </div>
              <button
                type="submit"
                disabled={busy}
                className="self-end rounded-md bg-brand px-3.5 py-2.5 text-sm font-medium text-ink transition-colors hover:bg-brand/90 disabled:opacity-40"
              >
                Create
              </button>
            </form>
            {organizations === null ? (
              <p className="text-sm text-mist">Loading organizations…</p>
            ) : (
              <ul className="divide-y divide-white/[0.06] text-sm">
                {organizations.map((organization) => (
                  <li
                    key={organization.organization_id}
                    className="flex items-center justify-between py-2.5"
                  >
                    <div>
                      <div>{organization.name}</div>
                      <div className="text-xs text-mist">{organization.slug}</div>
                    </div>
                    <Link
                      to={`/organizations/${organization.organization_id}/members`}
                      className="text-xs text-brand"
                    >
                      Members →
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="rounded-lg bg-ink-850 p-5 outline-1 -outline-offset-1 outline-white/[0.06]">
            <h2 className="font-display text-sm font-medium">Users</h2>
            <p className="mt-1 mb-4 text-xs text-mist">
              Everyone who has signed in. Platform admins reach every organization; grant it
              sparingly.
            </p>
            {users === null ? (
              <p className="text-sm text-mist">Loading users…</p>
            ) : (
              <ul className="divide-y divide-white/[0.06] text-sm">
                {users.map((entry) => (
                  <li key={entry.user_id} className="flex items-center justify-between py-2.5">
                    <div>
                      <div>{entry.display_name ?? entry.email}</div>
                      {entry.display_name !== null && (
                        <div className="text-xs text-mist">{entry.email}</div>
                      )}
                    </div>
                    <label className="flex items-center gap-2 text-xs text-mist">
                      <input
                        type="checkbox"
                        checked={entry.is_platform_admin}
                        disabled={busy || entry.user_id === user?.user_id}
                        onChange={(event) => void setPlatformAdmin(entry, event.target.checked)}
                        aria-label={`Platform admin: ${entry.email}`}
                      />
                      Platform admin
                    </label>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </main>
    </AppShell>
  )
}
