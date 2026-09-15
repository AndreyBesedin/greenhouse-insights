import { useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { authMode } from '../auth/session'
import { useSession } from '../auth/SessionContext'
import { CropIcon } from '../components/CropIcon'

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { signIn, subject: signedInAs } = useSession()
  const mode = authMode()
  const [subject, setSubject] = useState('dev-admin')
  const from = (location.state as { from?: string } | null)?.from ?? '/'

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    if (mode === 'oidc') {
      // Hands off to the identity provider; the redirect comes back to /.
      signIn(from)
      return
    }
    if (!subject.trim()) {
      return
    }
    signIn(subject)
    navigate(from, { replace: true })
  }

  if (mode === 'oidc' && signedInAs !== null) {
    navigate(from, { replace: true })
  }

  return (
    <main className="grid min-h-screen bg-ink font-sans text-paper md:grid-cols-2">
      <section className="flex flex-col justify-center px-8 py-16 md:px-16 lg:px-24">
        <div className="max-w-[34ch]">
          <div className="mb-8 flex items-center gap-2.5">
            <span className="grid size-9 place-items-center rounded-md bg-brand/15 text-brand outline-1 -outline-offset-1 outline-brand/30">
              <CropIcon crop="cherry-tomato" size="md" />
            </span>
            <span className="font-display text-lg font-semibold tracking-tight">
              Greenhouse Insights
            </span>
          </div>
          <h1 className="max-w-[30ch] text-balance font-display text-3xl font-medium leading-tight tracking-tight">
            Greenhouse intelligence, from plant to production
          </h1>
          <p className="mt-4 max-w-[40ch] text-pretty text-sm text-mist">
            Track every plant, every day — a calm cockpit your growers keep open from first light to
            last pick.
          </p>
        </div>
      </section>

      <section className="flex items-center justify-center px-8 py-16">
        <form
          onSubmit={onSubmit}
          className="w-full max-w-sm rounded-lg bg-ink-850 p-6 outline-1 -outline-offset-1 outline-white/[0.06]"
        >
          <div className="mb-1 text-sm font-medium">Sign in to your greenhouse</div>
          <p className="mb-4 text-xs text-mist">
            Development mode: the API trusts whatever identity you type here. Use the subject listed
            in GREENHOUSE_PLATFORM_ADMIN_SUBJECTS to sign in as a platform admin.
          </p>
          <label htmlFor="subject" className="mb-1.5 block text-xs text-mist">
            Identity subject
          </label>
          <input
            id="subject"
            type="text"
            required
            autoFocus
            value={subject}
            onChange={(event) => setSubject(event.target.value)}
            className="mb-5 w-full rounded-md bg-ink-800 px-3.5 py-2.5 text-sm text-paper outline-1 -outline-offset-1 outline-white/[0.07] placeholder:text-mist focus:outline-brand/50"
          />
          <button
            type="submit"
            className="block w-full rounded-md bg-brand py-2.5 text-center text-sm font-medium text-ink transition-colors hover:bg-brand/90"
          >
            Sign in
          </button>
        </form>
      </section>
    </main>
  )
}
