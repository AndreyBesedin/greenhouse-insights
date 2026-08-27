import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '../api/client'
import { useGreenhouseState } from './useGreenhouseState'

vi.mock('../api/client', () => ({
  apiClient: { GET: vi.fn() },
}))

const mockedGet = vi.mocked(apiClient.GET)

function ok<T>(data: T) {
  return { data, error: undefined, response: new Response() }
}

const STATE_DAY_1 = { greenhouse_id: 'gh_001', simulated_day: 1, plant_states: [] }
const STATE_DAY_2 = { greenhouse_id: 'gh_001', simulated_day: 2, plant_states: [] }

beforeEach(() => {
  mockedGet.mockReset()
})

describe('useGreenhouseState', () => {
  it('fetches state for the greenhouse on mount', async () => {
    mockedGet.mockResolvedValue(ok(STATE_DAY_1))

    const { result } = renderHook(() => useGreenhouseState('gh_001', 1))

    await waitFor(() => expect(result.current).toEqual(STATE_DAY_1))
    expect(mockedGet).toHaveBeenCalledWith('/greenhouses/{greenhouse_id}/state', {
      params: { path: { greenhouse_id: 'gh_001' }, query: { day: 1 } },
    })
  })

  it('refetches when currentStep changes', async () => {
    mockedGet.mockResolvedValueOnce(ok(STATE_DAY_1)).mockResolvedValueOnce(ok(STATE_DAY_2))

    const { result, rerender } = renderHook(
      ({ day }: { day: number }) => useGreenhouseState('gh_001', day),
      { initialProps: { day: 1 } },
    )
    await waitFor(() => expect(result.current).toEqual(STATE_DAY_1))

    rerender({ day: 2 })

    await waitFor(() => expect(result.current).toEqual(STATE_DAY_2))
    expect(mockedGet).toHaveBeenCalledTimes(2)
  })

  it('returns null when there is no state yet (404/no data)', async () => {
    mockedGet.mockResolvedValue({
      data: undefined,
      error: { detail: 'not found' },
      response: new Response(),
    })

    const { result } = renderHook(() => useGreenhouseState('gh_001', 0))

    await waitFor(() => expect(mockedGet).toHaveBeenCalled())
    expect(result.current).toBeNull()
  })
})
