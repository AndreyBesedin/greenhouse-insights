import '@testing-library/jest-dom/vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from './api/client'
import App from './App'
import { currentSubject, signIn, signOut } from './auth/session'

vi.mock('./api/client', () => ({
  apiClient: { GET: vi.fn() },
}))

const ME = {
  user_id: 'user_1',
  email: 'dev-admin@dev.local',
  display_name: 'dev-admin',
  is_platform_admin: true,
  organizations: [],
}

beforeEach(() => {
  signOut()
  vi.mocked(apiClient.GET).mockReset()
  vi.mocked(apiClient.GET).mockImplementation((async (path: string) => ({
    data: path === '/me' ? ME : [],
    error: undefined,
    response: new Response(),
  })) as never)
})

describe('App', () => {
  it('sends a visitor with no session to the login page', async () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>,
    )

    expect(await screen.findByRole('button', { name: /sign in/i })).toBeInTheDocument()
    expect(apiClient.GET).not.toHaveBeenCalled()
  })

  it('signs in from the login page and lands on the requested route', async () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>,
    )
    const user = userEvent.setup()
    await user.clear(await screen.findByLabelText(/identity subject/i))
    await user.type(screen.getByLabelText(/identity subject/i), 'dev-admin')

    await user.click(screen.getByRole('button', { name: /sign in/i }))

    expect(await screen.findByRole('heading', { name: /greenhouses/i })).toBeInTheDocument()
    expect(await screen.findByTestId('current-user')).toHaveTextContent('dev-admin')
  })

  it('signs out from the shell and returns to the login page', async () => {
    signIn('dev-admin')
    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>,
    )
    await screen.findByTestId('current-user')

    await userEvent.setup().click(screen.getByRole('button', { name: /sign out/i }))

    expect(await screen.findByRole('button', { name: /sign in/i })).toBeInTheDocument()
    expect(currentSubject()).toBeNull()
  })

  it('renders the greenhouse list at the root route once signed in', async () => {
    signIn('dev-admin')

    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>,
    )

    expect(await screen.findByRole('heading', { name: /greenhouses/i })).toBeInTheDocument()
    expect(await screen.findByTestId('current-user')).toHaveTextContent('dev-admin')
    expect(screen.getByText(/platform admin/i)).toBeInTheDocument()
  })
})
