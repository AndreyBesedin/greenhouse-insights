import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '../api/client'
import { memberOf, PLATFORM_ADMIN, withSession } from '../test/session'
import { GreenhouseListPage } from './GreenhouseListPage'

vi.mock('../api/client', () => ({
  apiClient: { GET: vi.fn(), DELETE: vi.fn() },
}))

const mockedGet = vi.mocked(apiClient.GET)
const mockedDelete = vi.mocked(apiClient.DELETE)

const GREENHOUSES = [
  {
    greenhouse_id: 'gh_001',
    organization_id: 'org_serrapulse_internal',
    name: 'Simulation Greenhouse 001',
    description: 'Primary demo greenhouse',
    source_type: 'SIMULATION',
    crop: 'cherry_tomato',
    plant_count: 40,
    compartment_count: 0,
    status: 'NOT_STARTED',
    current_step: 0,
    total_steps: 28,
    management_policy: 'DETERMINISTIC',
  },
  {
    greenhouse_id: 'gh_002',
    organization_id: 'org_serrapulse_internal',
    name: 'Longitudinal Plant Demo',
    description: 'Single-plant longitudinal demo',
    source_type: 'SIMULATION',
    crop: 'cherry_tomato',
    plant_count: 1,
    compartment_count: 0,
    status: 'NOT_STARTED',
    current_step: 0,
    total_steps: 40,
    management_policy: 'DETERMINISTIC',
  },
  {
    greenhouse_id: 'gh_demo',
    organization_id: 'org_serrapulse_internal',
    name: 'Agentic Demo Greenhouse',
    description: 'Recommended walkthrough greenhouse',
    source_type: 'SIMULATION',
    crop: 'cherry_tomato',
    plant_count: 6,
    compartment_count: 0,
    status: 'NOT_STARTED',
    current_step: 0,
    total_steps: 15,
    management_policy: 'AGENTIC',
  },
  {
    greenhouse_id: 'wur_agc4_2024',
    organization_id: 'org_serrapulse_internal',
    name: 'WUR AGC4 2024',
    description: 'Recorded history of six compartments.',
    source_type: 'IMPORTED_DATA',
    crop: 'dwarf_tomato',
    plant_count: 0,
    compartment_count: 6,
    status: null,
    current_step: null,
    total_steps: null,
    management_policy: null,
  },
]

beforeEach(() => {
  mockedGet.mockReset()
  mockedDelete.mockReset()
})

function renderList(user = PLATFORM_ADMIN, organizationId: string | null = null) {
  mockedGet.mockResolvedValue({ data: GREENHOUSES, error: undefined, response: new Response() })
  return render(
    withSession(
      <MemoryRouter>
        <GreenhouseListPage />
      </MemoryRouter>,
      user,
      { organizationId },
    ),
  )
}

describe('GreenhouseListPage', () => {
  it('renders a card for every greenhouse returned by the API', async () => {
    renderList()

    expect(await screen.findByText('Simulation Greenhouse 001')).toBeInTheDocument()
    expect(screen.getByText('Longitudinal Plant Demo')).toBeInTheDocument()
    expect(screen.getByText(/40 plants/)).toBeInTheDocument()
    expect(screen.getByText(/28 simulated days/)).toBeInTheDocument()
  })

  it('badges an imported greenhouse as recorded history', async () => {
    renderList()

    expect(await screen.findByText('WUR AGC4 2024')).toBeInTheDocument()
    expect(screen.getByText('Recorded history')).toBeInTheDocument()
    // exact match: compartments are counted instead of (absent) plants
    expect(screen.getByText('Dwarf Tomato · 6 compartments')).toBeInTheDocument()
  })

  it('badges the agentic greenhouse as the recommended demo', async () => {
    renderList()

    expect(await screen.findByText('Agentic Demo Greenhouse')).toBeInTheDocument()
    expect(screen.getByText('Recommended demo')).toBeInTheDocument()
    expect(screen.getByText(/Agentic \(scripted stand-in\)/)).toBeInTheDocument()
  })

  it('asks for confirmation before deleting, and cancel backs out without calling the API', async () => {
    const user = userEvent.setup()
    renderList()
    await screen.findByText('Simulation Greenhouse 001')

    await user.click(screen.getAllByRole('button', { name: 'Delete' })[0])
    expect(screen.getByText('Delete this greenhouse for good?')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(screen.queryByText('Delete this greenhouse for good?')).not.toBeInTheDocument()
    expect(mockedDelete).not.toHaveBeenCalled()
    expect(screen.getByText('Simulation Greenhouse 001')).toBeInTheDocument()
  })

  it('deletes the greenhouse and removes its card once confirmed', async () => {
    const user = userEvent.setup()
    mockedDelete.mockResolvedValue({ data: undefined, error: undefined, response: new Response() })
    renderList()
    await screen.findByText('Simulation Greenhouse 001')

    await user.click(screen.getAllByRole('button', { name: 'Delete' })[0])
    // gh_002's card still shows its own (unrelated) "Delete" trigger button,
    // so the confirm button for gh_001 is the first "Delete" in DOM order.
    await user.click(screen.getAllByRole('button', { name: 'Delete' })[0])

    expect(mockedDelete).toHaveBeenCalledWith('/greenhouses/{greenhouse_id}', {
      params: { path: { greenhouse_id: 'gh_001' } },
    })
    expect(await screen.findByText('Longitudinal Plant Demo')).toBeInTheDocument()
    expect(screen.queryByText('Simulation Greenhouse 001')).not.toBeInTheDocument()
  })

  it('shows an error and keeps the card when deletion fails', async () => {
    const user = userEvent.setup()
    mockedDelete.mockResolvedValue({
      data: undefined,
      error: {
        detail: [{ loc: ['path', 'greenhouse_id'], msg: 'not found', type: 'value_error' }],
      },
      response: new Response(),
    })
    renderList()
    await screen.findByText('Simulation Greenhouse 001')

    await user.click(screen.getAllByRole('button', { name: 'Delete' })[0])
    await user.click(screen.getAllByRole('button', { name: 'Delete' })[0])

    expect(await screen.findByText(/could not delete/i)).toBeInTheDocument()
    expect(screen.getByText('Simulation Greenhouse 001')).toBeInTheDocument()
  })

  it('hides creation and deletion from a viewer', async () => {
    renderList(memberOf('VIEWER'))

    expect(await screen.findByText('Simulation Greenhouse 001')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /new greenhouse/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Delete' })).not.toBeInTheDocument()
  })

  it('hides deletion from an editor too - only platform admins delete', async () => {
    renderList(memberOf('EDITOR'))

    expect(await screen.findByText('Simulation Greenhouse 001')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Delete' })).not.toBeInTheDocument()
  })

  it('shows only the selected organization when one is chosen', async () => {
    renderList(PLATFORM_ADMIN, 'org_acme')

    expect(await screen.findByText(/no greenhouses to show/i)).toBeInTheDocument()
    expect(screen.queryByText('Simulation Greenhouse 001')).not.toBeInTheDocument()
  })
})
