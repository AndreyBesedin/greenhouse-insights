import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'

import { apiClient } from '../api/client'
import {
  authMode,
  currentSubject,
  oidc,
  rememberOrganization,
  selectedOrganization,
  signIn as storeSubject,
  signOut as clearSubject,
} from './session'
import { SessionContext, useSession, type CurrentUser } from './SessionContext'

export function SessionProvider({ children }: { children: ReactNode }) {
  const mode = authMode()
  // In dev mode the subject is known synchronously; in oidc mode it is
  // known once the provider has finished any login redirect.
  const [subject, setSubject] = useState<string | null>(() =>
    mode === 'dev' ? currentSubject() : null,
  )
  const [initializing, setInitializing] = useState(mode === 'oidc')
  const [user, setUser] = useState<CurrentUser | null>(null)
  // Which subject `user` was loaded for, so a change of identity shows as
  // loading rather than briefly as the previous user.
  const [loadedFor, setLoadedFor] = useState<string | null>(null)
  const loading = initializing || (subject !== null && loadedFor !== subject)
  const [organizationId, setOrganizationId] = useState<string | null>(() => selectedOrganization())

  useEffect(() => {
    if (mode !== 'oidc') return
    let cancelled = false
    oidc()
      .bootstrap()
      .then((signedInAs) => {
        if (!cancelled) {
          setSubject(signedInAs)
          setInitializing(false)
        }
      })
      .catch(() => {
        if (!cancelled) setInitializing(false)
      })
    return () => {
      cancelled = true
    }
  }, [mode])

  useEffect(() => {
    if (subject === null) {
      return
    }
    let cancelled = false
    apiClient.GET('/me').then(({ data }) => {
      if (!cancelled) {
        setUser(data ?? null)
        setLoadedFor(subject)
      }
    })
    return () => {
      cancelled = true
    }
  }, [subject])

  const signIn = useCallback(
    (next: string) => {
      if (mode === 'oidc') {
        void oidc().login(next || '/')
        return
      }
      storeSubject(next)
      setSubject(currentSubject())
    },
    [mode],
  )

  const signOut = useCallback(() => {
    rememberOrganization(null)
    setSubject(null)
    setUser(null)
    setLoadedFor(null)
    setOrganizationId(null)
    if (mode === 'oidc') {
      void oidc().logout()
      return
    }
    clearSubject()
  }, [mode])

  const selectOrganization = useCallback((next: string | null) => {
    rememberOrganization(next)
    setOrganizationId(next)
  }, [])

  // A remembered organization the user can no longer reach is dropped.
  const reachable =
    organizationId === null ||
    user === null ||
    user.organizations.some((o) => o.organization_id === organizationId)
  const effectiveOrganizationId = reachable ? organizationId : null

  return (
    <SessionContext.Provider
      value={{
        subject,
        user,
        loading,
        initializing,
        organizationId: effectiveOrganizationId,
        selectOrganization,
        signIn,
        signOut,
      }}
    >
      {children}
    </SessionContext.Provider>
  )
}

/** Route guard: UX only - the backend enforces access regardless. */
export function RequireSession({ children }: { children: ReactNode }) {
  const { subject, initializing } = useSession()
  const location = useLocation()
  if (initializing) {
    return (
      <main className="grid min-h-screen place-items-center bg-ink text-sm text-mist">
        Signing in…
      </main>
    )
  }
  if (subject === null) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return children
}
