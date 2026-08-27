import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '../api/client'
import { GreenhouseDashboardPage } from './GreenhouseDashboardPage'

vi.mock('../api/client', () => ({
  apiClient: { GET: vi.fn() },
}))

const mockedGet = vi.mocked(apiClient.GET)

const DETAIL = {
  greenhouse: {
    greenhouse_id: 'gh_001',
    name: 'Simulation Greenhouse 001',
    description: 'Primary demo greenhouse',
    source_type: 'SIMULATION',
    layout: { kind: 'grid', rows: 4, columns: 10 },
    plants: [],
    created_at: '2026-01-01T00:00:00Z',
    current_state_timestamp: null,
    latest_available_timestamp: null,
  },
  simulation: {
    simulation_id: 'sim_gh_001',
    status: 'NOT_STARTED',
    current_step: 0,
    total_steps: 28,
  },
}

beforeEach(() => {
  mockedGet.mockReset()
})

function renderDashboard() {
  return render(
    <MemoryRouter initialEntries={['/greenhouses/gh_001']}>
      <Routes>
        <Route path="/greenhouses/:greenhouseId" element={<GreenhouseDashboardPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('GreenhouseDashboardPage', () => {
  it('shows the greenhouse name and current progress out of total steps', async () => {
    mockedGet.mockResolvedValue({ data: DETAIL, error: undefined, response: new Response() })

    renderDashboard()

    expect(await screen.findByText('Simulation Greenhouse 001')).toBeInTheDocument()
    expect(screen.getByText('Day 0 / 28')).toBeInTheDocument()
  })

  it('renders a disabled run-simulation button before the backend wiring exists', async () => {
    mockedGet.mockResolvedValue({ data: DETAIL, error: undefined, response: new Response() })

    renderDashboard()

    const runButton = await screen.findByRole('button', { name: /run simulation/i })
    expect(runButton).toBeDisabled()
  })
})
