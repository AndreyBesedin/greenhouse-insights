import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'

import { apiClient } from '../api/client'
import {
  currentSubject,
  rememberOrganization,
  selectedOrganization,
  signIn as storeSubject,
  signOut as clearSubject,
} from './session'
import { SessionContext, useSession, type CurrentUser } from './SessionContext'

export function SessionProvider({ children }: { children: ReactNode }) {
  const [subject, setSubject] = useState<string | null>(() => currentSubject())
  const [user, setUser] = useState<CurrentUser | null>(null)
  // Which subject `user` was loaded for, so a change of identity shows as
  // loading rather than briefly as the previous user.
  const [loadedFor, setLoadedFor] = useState<string | null>(null)
  const loading = subject !== null && loadedFor !== subject
  const [organizationId, setOrganizationId] = useState<string | null>(() => selectedOrganization())

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

  const signIn = useCallback((next: string) => {
    storeSubject(next)
    setSubject(currentSubject())
  }, [])

  const signOut = useCallback(() => {
    clearSubject()
    rememberOrganization(null)
    setSubject(null)
    setUser(null)
    setLoadedFor(null)
    setOrganizationId(null)
  }, [])

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
  const { subject } = useSession()
  const location = useLocation()
  if (subject === null) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return children
}
