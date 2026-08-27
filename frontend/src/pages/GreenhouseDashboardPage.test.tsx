import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '../api/client'
import { GreenhouseDashboardPage } from './GreenhouseDashboardPage'

vi.mock('../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn() },
}))

const mockedGet = vi.mocked(apiClient.GET)
const mockedPost = vi.mocked(apiClient.POST)

function ok<T>(data: T) {
  return { data, error: undefined, response: new Response() }
}

const NOT_STARTED_DETAIL = {
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
} as const

const RUNNING_1 = {
  simulation_id: 'sim_gh_001',
  status: 'RUNNING',
  current_step: 1,
  total_steps: 28,
} as const
const COMPLETED = {
  simulation_id: 'sim_gh_001',
  status: 'COMPLETED',
  current_step: 28,
  total_steps: 28,
} as const

beforeEach(() => {
  mockedGet.mockReset()
  mockedPost.mockReset()
})

afterEach(() => {
  vi.useRealTimers()
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
    mockedGet.mockResolvedValue(ok(NOT_STARTED_DETAIL))

    renderDashboard()

    expect(await screen.findByText('Simulation Greenhouse 001')).toBeInTheDocument()
    expect(screen.getByText('Day 0 / 28')).toBeInTheDocument()
  })

  it('clicking run starts polling and updates progress until completion', async () => {
    mockedGet.mockResolvedValueOnce(ok(NOT_STARTED_DETAIL))
    mockedPost.mockResolvedValue(ok(NOT_STARTED_DETAIL.simulation))
    mockedGet.mockResolvedValueOnce(ok(RUNNING_1))
    mockedGet.mockResolvedValueOnce(ok(COMPLETED))

    renderDashboard()
    const runButton = await screen.findByRole('button', { name: /run simulation/i })
    expect(runButton).toBeEnabled()

    vi.useFakeTimers()

    await act(async () => {
      fireEvent.click(runButton)
    })
    expect(mockedPost).toHaveBeenCalledOnce()

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000)
    })
    expect(screen.getByText('Day 1 / 28')).toBeInTheDocument()

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000)
    })
    expect(screen.getByText('Day 28 / 28')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /run simulation/i })).toBeDisabled()
  })
})
