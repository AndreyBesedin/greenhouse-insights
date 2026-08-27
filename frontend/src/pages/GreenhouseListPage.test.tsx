import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '../api/client'
import { GreenhouseListPage } from './GreenhouseListPage'

vi.mock('../api/client', () => ({
  apiClient: { GET: vi.fn() },
}))

const mockedGet = vi.mocked(apiClient.GET)

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
  },
]

beforeEach(() => {
  mockedGet.mockReset()
})

describe('GreenhouseListPage', () => {
  it('renders a card for every greenhouse returned by the API', async () => {
    mockedGet.mockResolvedValue({ data: GREENHOUSES, error: undefined, response: new Response() })

    render(
      <MemoryRouter>
        <GreenhouseListPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Simulation Greenhouse 001')).toBeInTheDocument()
    expect(screen.getByText('Longitudinal Plant Demo')).toBeInTheDocument()
    expect(screen.getByText(/40 plants/)).toBeInTheDocument()
    expect(screen.getByText(/28 simulated days/)).toBeInTheDocument()
  })
})
