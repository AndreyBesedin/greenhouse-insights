import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '../api/client'
import { memberOf, withSession } from '../test/session'
import { OrganizationMembersPage } from './OrganizationMembersPage'

vi.mock('../api/client', () => ({
  apiClient: { GET: vi.fn(), PUT: vi.fn(), DELETE: vi.fn() },
}))

const mockedGet = vi.mocked(apiClient.GET)
const mockedPut = vi.mocked(apiClient.PUT)
const mockedDelete = vi.mocked(apiClient.DELETE)

const MEMBERS = [
  {
    user_id: 'user_1',
    email: 'admin@acme.example',
    display_name: 'Ada',
    role: 'ORGANIZATION_ADMIN',
  },
  { user_id: 'user_2', email: 'viewer@acme.example', display_name: null, role: 'VIEWER' },
]

function ok<T>(data: T, status = 200) {
  return { data, error: undefined, response: new Response(null, { status }) }
}

beforeEach(() => {
  mockedGet.mockReset()
  mockedPut.mockReset()
  mockedDelete.mockReset()
  mockedGet.mockResolvedValue(ok(MEMBERS) as never)
})

function renderPage(user = memberOf('ORGANIZATION_ADMIN', 'org_acme')) {
  return render(
    withSession(
      <MemoryRouter initialEntries={['/organizations/org_acme/members']}>
        <Routes>
          <Route
            path="/organizations/:organizationId/members"
            element={<OrganizationMembersPage />}
          />
        </Routes>
      </MemoryRouter>,
      user,
    ),
  )
}

describe('OrganizationMembersPage', () => {
  it('lists the members with their roles', async () => {
    renderPage()

    expect(await screen.findByText('Ada')).toBeInTheDocument()
    expect(screen.getByText('viewer@acme.example')).toBeInTheDocument()
    expect(screen.getByLabelText('Role of viewer@acme.example')).toHaveValue('VIEWER')
  })

  it('adds a member by email and role', async () => {
    const user = userEvent.setup()
    mockedPut.mockResolvedValue(
      ok({
        user_id: 'user_3',
        email: 'new@acme.example',
        display_name: null,
        role: 'EDITOR',
      }) as never,
    )
    renderPage()
    await screen.findByText('Ada')

    await user.type(screen.getByLabelText(/email of a user/i), 'new@acme.example')
    await user.selectOptions(screen.getByLabelText('Role'), 'EDITOR')
    await user.click(screen.getByRole('button', { name: /add member/i }))

    expect(mockedPut).toHaveBeenCalledWith('/organizations/{organization_id}/members', {
      params: { path: { organization_id: 'org_acme' } },
      body: { email: 'new@acme.example', role: 'EDITOR' },
    })
    expect(await screen.findByText('new@acme.example')).toBeInTheDocument()
  })

  it('explains when the person has never signed in', async () => {
    const user = userEvent.setup()
    mockedPut.mockResolvedValue({
      data: undefined,
      error: { detail: 'no user' },
      response: new Response(null, { status: 404 }),
    } as never)
    renderPage()
    await screen.findByText('Ada')

    await user.type(screen.getByLabelText(/email of a user/i), 'ghost@acme.example')
    await user.click(screen.getByRole('button', { name: /add member/i }))

    expect(await screen.findByText(/has signed in yet/i)).toBeInTheDocument()
  })

  it('removes a member', async () => {
    const user = userEvent.setup()
    mockedDelete.mockResolvedValue(ok(undefined, 204) as never)
    renderPage()
    await screen.findByText('Ada')

    await user.click(screen.getAllByRole('button', { name: 'Remove' })[1]!)

    expect(mockedDelete).toHaveBeenCalledWith(
      '/organizations/{organization_id}/members/{user_id}',
      { params: { path: { organization_id: 'org_acme', user_id: 'user_2' } } },
    )
    expect(screen.queryByText('viewer@acme.example')).not.toBeInTheDocument()
  })

  it('tells an editor this page is for organization admins', async () => {
    renderPage(memberOf('EDITOR', 'org_acme'))

    expect(await screen.findByText(/only organization admins/i)).toBeInTheDocument()
  })
})
