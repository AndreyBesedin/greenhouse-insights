import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '../api/client'
import { GreenhouseListPage } from './GreenhouseListPage'

vi.mock('../api/client', () => ({
  apiClient: { GET: vi.fn(), DELETE: vi.fn() },
}))

const mockedGet = vi.mocked(apiClient.GET)
const mockedDelete = vi.mocked(apiClient.DELETE)

const GREENHOUSES = [
  {
    greenhouse_id: 'gh_001',
    name: 'Simulation Greenhouse 001',
    description: 'Primary demo greenhouse',
    source_type: 'SIMULATION',
    crop: 'cherry_tomato',
    plant_count: 40,
    status: 'NOT_STARTED',
    current_step: 0,
    total_steps: 28,
    management_policy: 'DETERMINISTIC',
  },
  {
    greenhouse_id: 'gh_002',
    name: 'Longitudinal Plant Demo',
    description: 'Single-plant longitudinal demo',
    source_type: 'SIMULATION',
    crop: 'cherry_tomato',
    plant_count: 1,
    status: 'NOT_STARTED',
    current_step: 0,
    total_steps: 40,
    management_policy: 'DETERMINISTIC',
  },
  {
    greenhouse_id: 'gh_demo',
    name: 'Agentic Demo Greenhouse',
    description: 'Recommended walkthrough greenhouse',
    source_type: 'SIMULATION',
    crop: 'cherry_tomato',
    plant_count: 6,
    status: 'NOT_STARTED',
    current_step: 0,
    total_steps: 15,
    management_policy: 'AGENTIC',
  },
  {
    greenhouse_id: 'wur_agc4_2024_c306',
    name: 'WUR AGC4 2024 · compartment 3.06 (Reference)',
    description: 'Recorded history of compartment 3.06.',
    source_type: 'IMPORTED_DATA',
    crop: 'dwarf_tomato',
    plant_count: 0,
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

function renderList() {
  mockedGet.mockResolvedValue({ data: GREENHOUSES, error: undefined, response: new Response() })
  return render(
    <MemoryRouter>
      <GreenhouseListPage />
    </MemoryRouter>,
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

    expect(await screen.findByText(/compartment 3\.06/)).toBeInTheDocument()
    expect(screen.getByText('Recorded history')).toBeInTheDocument()
    // exact match: no plant count is appended for a compartment without plants
    expect(screen.getByText('Dwarf Tomato')).toBeInTheDocument()
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
})
