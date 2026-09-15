import { createContext, useContext } from 'react'

import type { components } from '../../generated/schema'

export type CurrentUser = components['schemas']['CurrentUser']

export type SessionState = {
  /** The dev subject signed in as, or null when nobody is. */
  subject: string | null
  /** The signed-in user as the API sees them; null until loaded or when signed out. */
  user: CurrentUser | null
  loading: boolean
  signIn: (subject: string) => void
  signOut: () => void
}

export const SessionContext = createContext<SessionState>({
  subject: null,
  user: null,
  loading: false,
  signIn: () => {},
  signOut: () => {},
})

export function useSession(): SessionState {
  return useContext(SessionContext)
}
