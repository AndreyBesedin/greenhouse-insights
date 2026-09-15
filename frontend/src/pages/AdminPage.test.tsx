import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '../api/client'
import { memberOf, PLATFORM_ADMIN, withSession } from '../test/session'
import { AdminPage } from './AdminPage'

vi.mock('../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn() },
}))

const mockedGet = vi.mocked(apiClient.GET)
const mockedPost = vi.mocked(apiClient.POST)
const mockedPut = vi.mocked(apiClient.PUT)

const ORGANIZATIONS = [
  {
    organization_id: 'org_serrapulse_internal',
    name: 'SerraPulse Internal',
    slug: 'serrapulse-internal',
    role: null,
  },
]
const USERS = [
  {
    user_id: 'user_root',
    email: 'dev-admin@dev.local',
    display_name: 'dev-admin',
    is_platform_admin: true,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    user_id: 'user_2',
    email: 'someone@dev.local',
    display_name: null,
    is_platform_admin: false,
    created_at: '2026-01-02T00:00:00Z',
  },
]

function ok<T>(data: T, status = 200) {
  return { data, error: undefined, response: new Response(null, { status }) }
}

beforeEach(() => {
  mockedGet.mockReset()
  mockedPost.mockReset()
  mockedPut.mockReset()
  mockedGet.mockImplementation(((path: string) =>
    Promise.resolve(ok(path === '/organizations' ? ORGANIZATIONS : USERS))) as never)
})

function renderPage(user = PLATFORM_ADMIN) {
  return render(
    withSession(
      <MemoryRouter>
        <AdminPage />
      </MemoryRouter>,
      user,
    ),
  )
}

describe('AdminPage', () => {
  it('lists organizations and users', async () => {
    renderPage()

    expect(await screen.findByText('SerraPulse Internal')).toBeInTheDocument()
    expect(screen.getByText('someone@dev.local')).toBeInTheDocument()
    expect(screen.getByLabelText('Platform admin: dev-admin@dev.local')).toBeChecked()
    expect(screen.getByLabelText('Platform admin: dev-admin@dev.local')).toBeDisabled()
  })

  it('creates an organization', async () => {
    const user = userEvent.setup()
    mockedPost.mockResolvedValue(
      ok(
        {
          organization_id: 'org_x',
          name: 'Acme',
          slug: 'acme',
          created_at: '2026-01-03T00:00:00Z',
        },
        201,
      ) as never,
    )
    renderPage()
    await screen.findByText('SerraPulse Internal')

    await user.type(screen.getByLabelText('Name'), 'Acme')
    await user.type(screen.getByLabelText('Slug'), 'acme')
    await user.click(screen.getByRole('button', { name: 'Create' }))

    expect(mockedPost).toHaveBeenCalledWith('/organizations', {
      body: { name: 'Acme', slug: 'acme' },
    })
    expect(await screen.findByText('Acme')).toBeInTheDocument()
  })

  it('grants platform admin to another user', async () => {
    const user = userEvent.setup()
    mockedPut.mockResolvedValue(ok({ ...USERS[1], is_platform_admin: true }) as never)
    renderPage()
    await screen.findByText('someone@dev.local')

    await user.click(screen.getByLabelText('Platform admin: someone@dev.local'))

    expect(mockedPut).toHaveBeenCalledWith('/admin/users/{user_id}/platform-admin', {
      params: { path: { user_id: 'user_2' } },
      body: { is_platform_admin: true },
    })
    expect(screen.getByLabelText('Platform admin: someone@dev.local')).toBeChecked()
  })

  it('turns away a non-platform-admin', async () => {
    renderPage(memberOf('ORGANIZATION_ADMIN'))

    expect(await screen.findByText(/only platform admins/i)).toBeInTheDocument()
  })
})
