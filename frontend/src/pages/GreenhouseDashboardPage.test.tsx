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

function notFound() {
  return { data: undefined, error: { detail: 'not found' }, response: new Response() }
}

const DETAIL = {
  greenhouse: {
    greenhouse_id: 'gh_001',
    name: 'Simulation Greenhouse 001',
    description: 'Primary demo greenhouse',
    source_type: 'SIMULATION',
    layout: { kind: 'grid', rows: 1, columns: 1 },
    plants: [{ plant_id: 'plant_017', variety: 'cherry_tomato', row: 1, position_in_row: 1 }],
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

const STATE_DAY_1 = {
  greenhouse_id: 'gh_001',
  simulated_day: 1,
  timestamp: '2026-01-01T00:00:00Z',
  plant_states: [
    {
      plant_id: 'plant_017',
      greenhouse_id: 'gh_001',
      simulated_day: 1,
      timestamp: '2026-01-01T00:00:00Z',
      health: 'HEALTHY',
      latest_soil_moisture_pct: 55,
      latest_visible_fruit_count: null,
      latest_ripe_fruit_count: null,
      last_event_type: null,
      last_event_timestamp: null,
      provenance: 'DETERMINISTICALLY_DERIVED',
    },
  ],
  plants_healthy: 1,
  plants_monitor: 0,
  plants_action_required: 0,
} as const

const PLANT_DETAIL = {
  plant: DETAIL.greenhouse.plants[0],
  state: STATE_DAY_1.plant_states[0],
} as const

function mockGetImplementation(path: string) {
  if (path === '/greenhouses/{greenhouse_id}') return Promise.resolve(ok(DETAIL))
  if (path === '/greenhouses/{greenhouse_id}/state') return Promise.resolve(notFound())
  if (path === '/simulations/{simulation_id}/status') return Promise.resolve(ok(RUNNING_1))
  if (path === '/greenhouses/{greenhouse_id}/plants/{plant_id}')
    return Promise.resolve(ok(PLANT_DETAIL))
  if (path === '/greenhouses/{greenhouse_id}/plants/{plant_id}/history')
    return Promise.resolve(ok([]))
  throw new Error(`unexpected GET ${path}`)
}

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
    mockedGet.mockImplementation((path: string) => mockGetImplementation(path))

    renderDashboard()

    expect(await screen.findByText('Simulation Greenhouse 001')).toBeInTheDocument()
    expect(screen.getByText('Day 0 / 28')).toBeInTheDocument()
  })

  it('renders the greenhouse map and a neutral KPI bar before any state exists', async () => {
    mockedGet.mockImplementation((path: string) => mockGetImplementation(path))

    renderDashboard()

    expect(await screen.findByRole('button', { name: /plant_017/ })).toBeInTheDocument()
    expect(screen.getByText('0 healthy | 0 monitor | 0 action required')).toBeInTheDocument()
  })

  it('selecting a plant fetches and shows its detail', async () => {
    mockedGet.mockImplementation((path: string) => mockGetImplementation(path))

    renderDashboard()
    const cell = await screen.findByRole('button', { name: /plant_017/ })

    await act(async () => {
      fireEvent.click(cell)
    })

    expect(await screen.findByText('Row 1 · Position 1')).toBeInTheDocument()
  })

  it('clicking run starts polling and updates progress and KPIs until completion', async () => {
    mockedGet.mockImplementation((path: string) => mockGetImplementation(path))
    mockedPost.mockResolvedValue(ok(DETAIL.simulation))

    renderDashboard()
    const runButton = await screen.findByRole('button', { name: /run simulation/i })
    expect(runButton).toBeEnabled()

    vi.useFakeTimers()

    await act(async () => {
      fireEvent.click(runButton)
    })
    expect(mockedPost).toHaveBeenCalledOnce()

    mockedGet.mockImplementation((path: string) => {
      if (path === '/greenhouses/{greenhouse_id}/state') return Promise.resolve(ok(STATE_DAY_1))
      return mockGetImplementation(path)
    })

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000)
    })
    expect(screen.getByText('Day 1 / 28')).toBeInTheDocument()
    expect(screen.getByText('1 healthy | 0 monitor | 0 action required')).toBeInTheDocument()
  })

  it('navigating to a past day updates the KPI bar and returning restores the current day', async () => {
    const COMPLETED_DETAIL = {
      ...DETAIL,
      simulation: { ...DETAIL.simulation, status: 'COMPLETED', current_step: 28 },
    } as const
    const STATE_DAY_28 = {
      ...STATE_DAY_1,
      simulated_day: 28,
      plant_states: [{ ...STATE_DAY_1.plant_states[0], health: 'ACTION_REQUIRED' }],
      plants_healthy: 0,
      plants_action_required: 1,
    }

    mockedGet.mockImplementation(
      (path: string, options?: { params?: { query?: { day?: number } } }) => {
        if (path === '/greenhouses/{greenhouse_id}') return Promise.resolve(ok(COMPLETED_DETAIL))
        if (path === '/greenhouses/{greenhouse_id}/state') {
          const day = options?.params?.query?.day
          return Promise.resolve(ok(day === 14 ? STATE_DAY_1 : STATE_DAY_28))
        }
        return mockGetImplementation(path)
      },
    )

    renderDashboard()
    await screen.findByText('Day 28 / 28')
    expect(await screen.findByText('0 healthy | 0 monitor | 1 action required')).toBeInTheDocument()

    await act(async () => {
      fireEvent.change(screen.getByLabelText('Day'), { target: { value: '14' } })
    })

    expect(await screen.findByText(/viewing day 14/i)).toBeInTheDocument()
    expect(await screen.findByText('1 healthy | 0 monitor | 0 action required')).toBeInTheDocument()

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /return to current day/i }))
    })

    expect(screen.queryByText(/viewing day/i)).not.toBeInTheDocument()
    expect(await screen.findByText('0 healthy | 0 monitor | 1 action required')).toBeInTheDocument()
  })
})
