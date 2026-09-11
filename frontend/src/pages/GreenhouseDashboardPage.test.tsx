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
    management_policy: 'DETERMINISTIC',
    action_executor: 'SIMULATED_OPERATOR',
  },
} as const

const RUNNING_1 = {
  ...DETAIL.simulation,
  status: 'RUNNING',
  current_step: 1,
} as const

// The seeded simulation starts on 2026-01-01 with one-day steps, so simulated
// day N is the checkpoint at 2026-01-0N T00:00 UTC.
function checkpoint(day: number) {
  return `2026-01-${String(day).padStart(2, '0')}T00:00:00+00:00`
}

function checkpointsFor(days: number) {
  return Array.from({ length: days }, (_, index) => checkpoint(index + 1))
}

const AT_1 = checkpoint(1)

const STATE_DAY_1 = {
  greenhouse_id: 'gh_001',
  timestamp: AT_1,
  plant_states: [
    {
      plant_id: 'plant_017',
      greenhouse_id: 'gh_001',
      timestamp: AT_1,
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
  if (path === '/greenhouses/{greenhouse_id}/timeline')
    return Promise.resolve(ok({ checkpoints: [], current_timestamp: null }))
  if (path === '/simulations/{simulation_id}/status') return Promise.resolve(ok(RUNNING_1))
  if (path === '/greenhouses/{greenhouse_id}/plants/{plant_id}')
    return Promise.resolve(ok(PLANT_DETAIL))
  if (path === '/greenhouses/{greenhouse_id}/plants/{plant_id}/history')
    return Promise.resolve(ok([]))
  if (path === '/greenhouses/{greenhouse_id}/recommendations') return Promise.resolve(ok([]))
  if (path === '/simulations/{simulation_id}/management-progress') return Promise.resolve(ok(null))
  throw new Error(`unexpected GET ${path}`)
}

// A simulation that has advanced to day 1: one checkpoint, one state
// snapshot - the earliest point at which recommendations can exist.
function mockGetImplementationOnDay1(path: string) {
  if (path === '/greenhouses/{greenhouse_id}')
    return Promise.resolve(ok({ ...DETAIL, simulation: RUNNING_1 }))
  if (path === '/greenhouses/{greenhouse_id}/state') return Promise.resolve(ok(STATE_DAY_1))
  if (path === '/greenhouses/{greenhouse_id}/timeline')
    return Promise.resolve(ok({ checkpoints: [AT_1], current_timestamp: AT_1 }))
  return mockGetImplementation(path)
}

function timelineOf(days: number) {
  const checkpoints = checkpointsFor(days)
  return { checkpoints, current_timestamp: checkpoints[days - 1] }
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

  it('clicking next day advances one day and updates progress and KPIs', async () => {
    mockedGet.mockImplementation((path: string) => mockGetImplementation(path))
    mockedPost.mockResolvedValue(ok(RUNNING_1))

    renderDashboard()
    const nextDayButton = await screen.findByRole('button', { name: 'Next day →' })
    expect(nextDayButton).toBeEnabled()

    mockedGet.mockImplementation((path: string) => {
      if (path === '/greenhouses/{greenhouse_id}/state') return Promise.resolve(ok(STATE_DAY_1))
      return mockGetImplementation(path)
    })

    await act(async () => {
      fireEvent.click(nextDayButton)
    })

    expect(mockedPost).toHaveBeenCalledWith('/simulations/{simulation_id}/next-day', {
      params: {
        path: { simulation_id: 'sim_gh_001' },
        query: { confirm_dismiss_remaining: false },
      },
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
      timestamp: checkpoint(28),
      plant_states: [{ ...STATE_DAY_1.plant_states[0], health: 'ACTION_REQUIRED' }],
      plants_healthy: 0,
      plants_action_required: 1,
    }

    mockedGet.mockImplementation(
      (path: string, options?: { params?: { query?: { at?: string } } }) => {
        if (path === '/greenhouses/{greenhouse_id}') return Promise.resolve(ok(COMPLETED_DETAIL))
        if (path === '/greenhouses/{greenhouse_id}/timeline')
          return Promise.resolve(ok(timelineOf(28)))
        if (path === '/greenhouses/{greenhouse_id}/state') {
          const at = options?.params?.query?.at
          return Promise.resolve(ok(at === checkpoint(14) ? STATE_DAY_1 : STATE_DAY_28))
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

  it('shows a pending recommendation and approving it marks it executed', async () => {
    const pending = {
      recommendation_id: 'rec_1',
      source: { type: 'SIMULATION', source_id: 'sim_gh_001' },
      greenhouse_id: 'gh_001',
      context_timestamp: AT_1,
      plant_id: 'plant_017',
      action: { action_type: 'WATER_PLANT', plant_id: 'plant_017', amount_ml: 700 },
      source_policy: 'DETERMINISTIC',
      status: 'PENDING',
      reason: 'Soil moisture at 12%.',
      evidence: { soil_moisture_pct: 12 },
      rejection_reason: null,
      approved_by: null,
      executed_by: null,
      requested_at: '2026-01-01T00:00:00Z',
      reviewed_at: null,
      executed_at: null,
    } as const
    mockedGet.mockImplementation((path: string) => {
      if (path === '/greenhouses/{greenhouse_id}/recommendations')
        return Promise.resolve(ok([pending]))
      return mockGetImplementationOnDay1(path)
    })
    mockedPost.mockResolvedValue(ok({ ...pending, status: 'EXECUTED', approved_by: 'HUMAN' }))

    renderDashboard()

    expect(await screen.findByText('plant_017 · Water')).toBeInTheDocument()
    expect(screen.getByText('Soil moisture at 12%.')).toBeInTheDocument()
    const approveButton = screen.getByRole('button', { name: 'Water 700 ml' })

    await act(async () => {
      fireEvent.click(approveButton)
    })

    expect(mockedPost).toHaveBeenCalledWith('/recommendations/{recommendation_id}/approve', {
      params: { path: { recommendation_id: 'rec_1' } },
    })
    expect(await screen.findByText('Executed')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Water 700 ml' })).not.toBeInTheDocument()
  })

  it('recovers cleanly when approving a recommendation throws', async () => {
    const pending = {
      recommendation_id: 'rec_1',
      source: { type: 'SIMULATION', source_id: 'sim_gh_001' },
      greenhouse_id: 'gh_001',
      context_timestamp: AT_1,
      plant_id: 'plant_017',
      action: { action_type: 'WATER_PLANT', plant_id: 'plant_017', amount_ml: 700 },
      source_policy: 'DETERMINISTIC',
      status: 'PENDING',
      reason: 'Soil moisture at 12%.',
      evidence: {},
      rejection_reason: null,
      approved_by: null,
      executed_by: null,
      requested_at: '2026-01-01T00:00:00Z',
      reviewed_at: null,
      executed_at: null,
    } as const
    mockedGet.mockImplementation((path: string) => {
      if (path === '/greenhouses/{greenhouse_id}/recommendations')
        return Promise.resolve(ok([pending]))
      return mockGetImplementationOnDay1(path)
    })
    mockedPost.mockRejectedValue(new TypeError('Failed to fetch'))

    renderDashboard()
    const approveButton = await screen.findByRole('button', { name: 'Water 700 ml' })

    await act(async () => {
      fireEvent.click(approveButton)
    })

    // The busy flag must clear (not get stuck) and the recommendation must
    // stay reviewable so the operator can retry.
    expect(await screen.findByText(/Could not approve that recommendation/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Water 700 ml' })).toBeEnabled()

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Close' }))
    })
    expect(screen.queryByText(/Could not approve that recommendation/)).not.toBeInTheDocument()
  })

  it('disables next day while a single approval is still in flight', async () => {
    const pending = {
      recommendation_id: 'rec_1',
      source: { type: 'SIMULATION', source_id: 'sim_gh_001' },
      greenhouse_id: 'gh_001',
      context_timestamp: AT_1,
      plant_id: 'plant_017',
      action: { action_type: 'WATER_PLANT', plant_id: 'plant_017', amount_ml: 700 },
      source_policy: 'DETERMINISTIC',
      status: 'PENDING',
      reason: 'Soil moisture at 12%.',
      evidence: {},
      rejection_reason: null,
      approved_by: null,
      executed_by: null,
      requested_at: '2026-01-01T00:00:00Z',
      reviewed_at: null,
      executed_at: null,
    } as const
    mockedGet.mockImplementation((path: string) => {
      if (path === '/greenhouses/{greenhouse_id}/recommendations')
        return Promise.resolve(ok([pending]))
      return mockGetImplementationOnDay1(path)
    })
    let resolveApprove: (() => void) | null = null
    mockedPost.mockImplementation((path: string) => {
      if (path === '/recommendations/{recommendation_id}/approve') {
        return new Promise((resolve) => {
          resolveApprove = () =>
            resolve(ok({ ...pending, status: 'EXECUTED', approved_by: 'HUMAN' }))
        })
      }
      return Promise.resolve(ok(RUNNING_1))
    })

    renderDashboard()
    const nextDayButton = await screen.findByRole('button', { name: 'Next day →' })
    expect(nextDayButton).toBeEnabled()
    const approveButton = await screen.findByRole('button', { name: 'Water 700 ml' })

    await act(async () => {
      fireEvent.click(approveButton)
    })

    expect(screen.getByRole('button', { name: 'Reviewing…' })).toBeDisabled()

    await act(async () => {
      resolveApprove?.()
    })

    expect(await screen.findByRole('button', { name: 'Next day →' })).toBeEnabled()
  })

  it('approve all executes every pending recommendation in one click', async () => {
    const pendingA = {
      recommendation_id: 'rec_1',
      source: { type: 'SIMULATION', source_id: 'sim_gh_001' },
      greenhouse_id: 'gh_001',
      context_timestamp: AT_1,
      plant_id: 'plant_017',
      action: { action_type: 'WATER_PLANT', plant_id: 'plant_017', amount_ml: 700 },
      source_policy: 'DETERMINISTIC',
      status: 'PENDING',
      reason: 'Soil moisture at 12%.',
      evidence: {},
      rejection_reason: null,
      approved_by: null,
      executed_by: null,
      requested_at: '2026-01-01T00:00:00Z',
      reviewed_at: null,
      executed_at: null,
    } as const
    const pendingB = {
      ...pendingA,
      recommendation_id: 'rec_2',
      plant_id: 'plant_018',
      action: { action_type: 'HARVEST_PLANT', plant_id: 'plant_018' },
      reason: 'Ripe fruit ready.',
    } as const
    mockedGet.mockImplementation((path: string) => {
      if (path === '/greenhouses/{greenhouse_id}/recommendations')
        return Promise.resolve(ok([pendingA, pendingB]))
      return mockGetImplementationOnDay1(path)
    })
    mockedPost.mockResolvedValue(
      ok([
        { ...pendingA, status: 'EXECUTED', approved_by: 'HUMAN' },
        { ...pendingB, status: 'EXECUTED', approved_by: 'HUMAN' },
      ]),
    )

    renderDashboard()
    const approveAllButton = await screen.findByRole('button', { name: 'Approve all (2)' })

    await act(async () => {
      fireEvent.click(approveAllButton)
    })

    expect(mockedPost).toHaveBeenCalledWith(
      '/greenhouses/{greenhouse_id}/recommendations/approve-all',
      { params: { path: { greenhouse_id: 'gh_001' }, query: { at: AT_1 } } },
    )
    expect(await screen.findAllByText('Executed')).toHaveLength(2)
    expect(screen.queryByRole('button', { name: 'Approve all (2)' })).not.toBeInTheDocument()
  })

  it('hides approve all when only one recommendation is pending', async () => {
    const pending = {
      recommendation_id: 'rec_1',
      source: { type: 'SIMULATION', source_id: 'sim_gh_001' },
      greenhouse_id: 'gh_001',
      context_timestamp: AT_1,
      plant_id: 'plant_017',
      action: { action_type: 'WATER_PLANT', plant_id: 'plant_017', amount_ml: 700 },
      source_policy: 'DETERMINISTIC',
      status: 'PENDING',
      reason: 'Soil moisture at 12%.',
      evidence: {},
      rejection_reason: null,
      approved_by: null,
      executed_by: null,
      requested_at: '2026-01-01T00:00:00Z',
      reviewed_at: null,
      executed_at: null,
    } as const
    mockedGet.mockImplementation((path: string) => {
      if (path === '/greenhouses/{greenhouse_id}/recommendations')
        return Promise.resolve(ok([pending]))
      return mockGetImplementationOnDay1(path)
    })

    renderDashboard()

    expect(await screen.findByText('plant_017 · Water')).toBeInTheDocument()
    expect(screen.queryByText(/Approve all/)).not.toBeInTheDocument()
  })

  it('the AI assistant panel starts open and collapses/expands on click', async () => {
    const pending = {
      recommendation_id: 'rec_1',
      source: { type: 'SIMULATION', source_id: 'sim_gh_001' },
      greenhouse_id: 'gh_001',
      context_timestamp: AT_1,
      plant_id: 'plant_017',
      action: { action_type: 'WATER_PLANT', plant_id: 'plant_017', amount_ml: 700 },
      source_policy: 'DETERMINISTIC',
      status: 'PENDING',
      reason: 'Soil moisture at 12%.',
      evidence: { soil_moisture_pct: 12 },
      rejection_reason: null,
      approved_by: null,
      executed_by: null,
      requested_at: '2026-01-01T00:00:00Z',
      reviewed_at: null,
      executed_at: null,
    } as const
    mockedGet.mockImplementation((path: string) => {
      if (path === '/greenhouses/{greenhouse_id}/recommendations')
        return Promise.resolve(ok([pending]))
      return mockGetImplementationOnDay1(path)
    })

    renderDashboard()
    expect(await screen.findByText('plant_017 · Water')).toBeInTheDocument()

    const toggle = screen.getByRole('button', { name: /AI assistant/ })
    expect(toggle).toHaveAttribute('aria-expanded', 'true')

    await act(async () => {
      fireEvent.click(toggle)
    })

    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByText('plant_017 · Water')).not.toBeInTheDocument()

    await act(async () => {
      fireEvent.click(toggle)
    })

    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('plant_017 · Water')).toBeInTheDocument()
  })

  it('recommendations are read-only when viewing a historical day', async () => {
    const COMPLETED_DETAIL = {
      ...DETAIL,
      simulation: { ...DETAIL.simulation, status: 'COMPLETED', current_step: 28 },
    } as const
    const resolved = {
      recommendation_id: 'rec_1',
      source: { type: 'SIMULATION', source_id: 'sim_gh_001' },
      greenhouse_id: 'gh_001',
      context_timestamp: checkpoint(14),
      plant_id: 'plant_017',
      action: { action_type: 'WATER_PLANT', plant_id: 'plant_017', amount_ml: 700 },
      source_policy: 'DETERMINISTIC',
      status: 'EXECUTED',
      reason: 'Soil moisture at 12%.',
      evidence: { soil_moisture_pct: 12 },
      rejection_reason: null,
      approved_by: 'HUMAN',
      executed_by: 'SIMULATED_OPERATOR',
      requested_at: '2026-01-14T00:00:00Z',
      reviewed_at: '2026-01-14T00:00:01Z',
      executed_at: '2026-01-14T00:00:01Z',
    } as const

    mockedGet.mockImplementation(
      (path: string, options?: { params?: { query?: { at?: string } } }) => {
        if (path === '/greenhouses/{greenhouse_id}') return Promise.resolve(ok(COMPLETED_DETAIL))
        if (path === '/greenhouses/{greenhouse_id}/timeline')
          return Promise.resolve(ok(timelineOf(28)))
        if (path === '/greenhouses/{greenhouse_id}/state') return Promise.resolve(ok(STATE_DAY_1))
        if (path === '/greenhouses/{greenhouse_id}/recommendations') {
          const at = options?.params?.query?.at
          return Promise.resolve(ok(at === checkpoint(14) ? [resolved] : []))
        }
        return mockGetImplementation(path)
      },
    )

    renderDashboard()
    await screen.findByText('Day 28 / 28')

    await act(async () => {
      fireEvent.change(screen.getByLabelText('Day'), { target: { value: '14' } })
    })

    expect(await screen.findByText('plant_017 · Water')).toBeInTheDocument()
    expect(screen.getByText('Executed')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Water 700 ml' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Dismiss' })).not.toBeInTheDocument()
  })

  it('next day shows a confirm prompt when recommendations are still pending, and proceeds when confirmed', async () => {
    mockedGet.mockImplementation((path: string) => mockGetImplementation(path))
    mockedPost.mockResolvedValueOnce({
      data: undefined,
      error: { detail: '1 pending recommendation(s) must be reviewed before advancing' },
      response: new Response(null, { status: 409 }),
    })
    mockedPost.mockResolvedValueOnce(ok(RUNNING_1))

    renderDashboard()
    const nextDayButton = await screen.findByRole('button', { name: 'Next day →' })

    await act(async () => {
      fireEvent.click(nextDayButton)
    })

    const confirmButton = await screen.findByRole('button', {
      name: 'Continue and dismiss remaining',
    })

    await act(async () => {
      fireEvent.click(confirmButton)
    })

    expect(mockedPost).toHaveBeenNthCalledWith(2, '/simulations/{simulation_id}/next-day', {
      params: {
        path: { simulation_id: 'sim_gh_001' },
        query: { confirm_dismiss_remaining: true },
      },
    })
    expect(
      screen.queryByRole('button', { name: 'Continue and dismiss remaining' }),
    ).not.toBeInTheDocument()
  })
})

describe('GreenhouseDashboardPage for a recorded greenhouse', () => {
  const RECORDED_DETAIL = {
    greenhouse: {
      greenhouse_id: 'wur_agc4_2024_c306',
      name: 'WUR AGC4 2024 · compartment 3.06 (Reference)',
      description: 'Recorded history of compartment 3.06.',
      source_type: 'IMPORTED_DATA',
      crop: 'dwarf_tomato',
      layout: { kind: 'compartment', rows: 0, columns: 0 },
      plants: [],
      created_at: '2024-09-02T22:05:00+00:00',
      current_state_timestamp: '2024-09-05T21:55:00+00:00',
      latest_available_timestamp: '2024-09-05T21:55:00+00:00',
    },
    simulation: null,
  } as const
  const CHECKPOINTS = [
    '2024-09-03T21:55:00+00:00',
    '2024-09-04T21:55:00+00:00',
    '2024-09-05T21:55:00+00:00',
  ]
  function recordedState(timestamp: string, airTemperatureC: number) {
    return {
      greenhouse_id: 'wur_agc4_2024_c306',
      timestamp,
      environment: {
        air_temperature_c: airTemperatureC,
        co2_ppm: 436,
        relative_humidity_pct: 80.5,
      },
      plant_states: [],
      plants_healthy: 0,
      plants_monitor: 0,
      plants_action_required: 0,
      total_ripe_mass_g: 0,
      total_harvested_g: 7119.65,
    }
  }

  function renderRecorded() {
    return render(
      <MemoryRouter initialEntries={['/greenhouses/wur_agc4_2024_c306']}>
        <Routes>
          <Route path="/greenhouses/:greenhouseId" element={<GreenhouseDashboardPage />} />
        </Routes>
      </MemoryRouter>,
    )
  }

  it('shows the latest recorded environment and lets the operator browse back in time', async () => {
    mockedGet.mockImplementation(
      (path: string, options?: { params?: { query?: { at?: string } } }) => {
        if (path === '/greenhouses/{greenhouse_id}') return Promise.resolve(ok(RECORDED_DETAIL))
        if (path === '/greenhouses/{greenhouse_id}/timeline')
          return Promise.resolve(
            ok({ checkpoints: CHECKPOINTS, current_timestamp: CHECKPOINTS[2] }),
          )
        if (path === '/greenhouses/{greenhouse_id}/state') {
          const at = options?.params?.query?.at
          return Promise.resolve(
            ok(
              at === CHECKPOINTS[0]
                ? recordedState(CHECKPOINTS[0], 19.2)
                : recordedState(CHECKPOINTS[2], 23.7),
            ),
          )
        }
        throw new Error(`unexpected GET ${path}`)
      },
    )

    renderRecorded()

    expect(await screen.findByText('Recorded history')).toBeInTheDocument()
    expect(await screen.findByText('23.7 °C')).toBeInTheDocument()
    expect(screen.getByText('436 ppm')).toBeInTheDocument()
    expect(screen.getByText('7.1 kg')).toBeInTheDocument()
    expect(screen.getByText('5 Sept 2024 of 3')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next day' })).toBeDisabled()

    await act(async () => {
      fireEvent.change(screen.getByLabelText('Day'), { target: { value: '1' } })
    })

    expect(await screen.findByText('19.2 °C')).toBeInTheDocument()
    expect(
      screen.getByText('Viewing 3 Sept 2024 — latest recorded state is 5 Sept 2024'),
    ).toBeInTheDocument()
  })
})
