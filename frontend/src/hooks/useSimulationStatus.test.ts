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
