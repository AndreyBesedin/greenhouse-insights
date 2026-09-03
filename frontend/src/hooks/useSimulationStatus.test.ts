import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '../api/client'
import { useSimulationStatus } from './useSimulationStatus'

vi.mock('../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn() },
}))

const mockedGet = vi.mocked(apiClient.GET)
const mockedPost = vi.mocked(apiClient.POST)

const NOT_STARTED = {
  simulation_id: 'sim_gh_002',
  status: 'NOT_STARTED',
  current_step: 0,
  total_steps: 3,
  management_policy: 'DETERMINISTIC',
  action_executor: 'SIMULATED_OPERATOR',
} as const
const RUNNING_1 = { ...NOT_STARTED, status: 'RUNNING', current_step: 1 } as const
const RUNNING_2 = { ...NOT_STARTED, status: 'RUNNING', current_step: 2 } as const
const COMPLETED = { ...NOT_STARTED, status: 'COMPLETED', current_step: 3 } as const

function ok<T>(data: T) {
  return { data, error: undefined, response: new Response() }
}

beforeEach(() => {
  mockedGet.mockReset()
  mockedPost.mockReset()
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('useSimulationStatus', () => {
  it('polls status after run() until COMPLETED, then stops polling', async () => {
    mockedPost.mockResolvedValue(ok(NOT_STARTED))
    mockedGet
      .mockResolvedValueOnce(ok(RUNNING_1))
      .mockResolvedValueOnce(ok(RUNNING_2))
      .mockResolvedValueOnce(ok(COMPLETED))

    const { result } = renderHook(() => useSimulationStatus('sim_gh_002', NOT_STARTED))

    await act(async () => {
      result.current.run()
    })
    expect(mockedPost).toHaveBeenCalledOnce()
    expect(result.current.isPolling).toBe(true)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000)
    })
    expect(result.current.status.current_step).toBe(1)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000)
    })
    expect(result.current.status.current_step).toBe(2)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000)
    })
    expect(result.current.status).toEqual(COMPLETED)
    expect(result.current.isPolling).toBe(false)

    const callsSoFar = mockedGet.mock.calls.length
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000)
    })
    expect(mockedGet.mock.calls.length).toBe(callsSoFar)
  })

  it('nextDay posts to the next-day endpoint and applies the returned status', async () => {
    mockedPost.mockResolvedValue(ok(RUNNING_1))

    const { result } = renderHook(() => useSimulationStatus('sim_gh_002', NOT_STARTED))

    expect(result.current.isAdvancing).toBe(false)

    await act(async () => {
      await result.current.nextDay()
    })

    expect(mockedPost).toHaveBeenCalledWith('/simulations/{simulation_id}/next-day', {
      params: {
        path: { simulation_id: 'sim_gh_002' },
        query: { confirm_dismiss_remaining: false },
      },
    })
    expect(result.current.status).toEqual(RUNNING_1)
    expect(result.current.isAdvancing).toBe(false)
  })

  it('nextDay reports blocked on a 409 without changing status', async () => {
    mockedPost.mockResolvedValue({
      data: undefined,
      error: { detail: 'pending recommendations' },
      response: new Response(null, { status: 409 }),
    })

    const { result } = renderHook(() => useSimulationStatus('sim_gh_002', NOT_STARTED))

    const outcome = await act(async () => result.current.nextDay())

    expect(outcome).toEqual({ blocked: true })
    expect(result.current.status).toEqual(NOT_STARTED)
  })

  it('polls analysis progress while nextDay is in flight, then clears it', async () => {
    let resolveNextDay: (() => void) | null = null
    mockedPost.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveNextDay = () => resolve(ok(RUNNING_1))
        }),
    )
    const progress = {
      simulation_id: 'sim_gh_002',
      simulated_day: 1,
      phase: 'ANALYZING',
      message: 'Inspecting plant_017…',
      plant_id: 'plant_017',
      completed_tool_calls: 1,
      recommendation_count: null,
    } as const
    mockedGet.mockResolvedValue(ok(progress))

    const { result } = renderHook(() => useSimulationStatus('sim_gh_002', NOT_STARTED))

    let nextDayPromise: Promise<{ blocked: boolean }> | null = null
    act(() => {
      nextDayPromise = result.current.nextDay()
    })
    expect(result.current.isAdvancing).toBe(true)
    expect(result.current.analysisProgress).toBeNull()

    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
    })
    expect(result.current.analysisProgress).toEqual(progress)

    await act(async () => {
      resolveNextDay?.()
      await nextDayPromise
    })
    expect(result.current.isAdvancing).toBe(false)
    expect(result.current.analysisProgress).toBeNull()
  })

  it('starts polling immediately when the initial status is already RUNNING', async () => {
    mockedGet.mockResolvedValueOnce(ok(COMPLETED))

    const { result } = renderHook(() => useSimulationStatus('sim_gh_002', RUNNING_2))

    expect(result.current.isPolling).toBe(true)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000)
    })
    expect(result.current.status).toEqual(COMPLETED)
    expect(result.current.isPolling).toBe(false)
  })
})
