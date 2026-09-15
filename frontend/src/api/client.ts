import createClient, { type Middleware } from 'openapi-fetch'

import type { paths } from '../../generated/schema'
import { authHeaders, authMode, signOut } from '../auth/session'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

// Attaches the session's credential to every request, and treats a 401 as
// the session having ended: clear it and send the user back to sign in.
const session: Middleware = {
  async onRequest({ request }) {
    for (const [name, value] of Object.entries(await authHeaders())) {
      request.headers.set(name, value)
    }
    return request
  },
  onResponse({ response }) {
    if (response.status === 401 && window.location.pathname !== '/login') {
      if (authMode() === 'dev') signOut()
      window.location.assign('/login')
    }
    return response
  },
}

export const apiClient = createClient<paths>({ baseUrl: BASE_URL })
apiClient.use(session)
