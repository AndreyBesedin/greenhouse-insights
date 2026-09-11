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

const AT_1 = '2026-01-01T00:00:00+00:00'
const AT_2 = '2026-01-02T00:00:00+00:00'
const STATE_DAY_1 = { greenhouse_id: 'gh_001', timestamp: AT_1, plant_states: [] }
const STATE_DAY_2 = { greenhouse_id: 'gh_001', timestamp: AT_2, plant_states: [] }

beforeEach(() => {
  mockedGet.mockReset()
})

describe('useGreenhouseState', () => {
  it('fetches state for the greenhouse on mount', async () => {
    mockedGet.mockResolvedValue(ok(STATE_DAY_1))

    const { result } = renderHook(() => useGreenhouseState('gh_001', AT_1))

    await waitFor(() => expect(result.current).toEqual(STATE_DAY_1))
    expect(mockedGet).toHaveBeenCalledWith('/greenhouses/{greenhouse_id}/state', {
      params: { path: { greenhouse_id: 'gh_001' }, query: { at: AT_1 } },
    })
  })

  it('refetches when the viewed instant changes', async () => {
    mockedGet.mockResolvedValueOnce(ok(STATE_DAY_1)).mockResolvedValueOnce(ok(STATE_DAY_2))

    const { result, rerender } = renderHook(
      ({ at }: { at: string }) => useGreenhouseState('gh_001', at),
      { initialProps: { at: AT_1 } },
    )
    await waitFor(() => expect(result.current).toEqual(STATE_DAY_1))

    rerender({ at: AT_2 })

    await waitFor(() => expect(result.current).toEqual(STATE_DAY_2))
    expect(mockedGet).toHaveBeenCalledTimes(2)
  })

  it('asks for the latest snapshot when no instant is given', async () => {
    mockedGet.mockResolvedValue(ok(STATE_DAY_2))

    const { result } = renderHook(() => useGreenhouseState('gh_001', null))

    await waitFor(() => expect(result.current).toEqual(STATE_DAY_2))
    expect(mockedGet).toHaveBeenCalledWith('/greenhouses/{greenhouse_id}/state', {
      params: { path: { greenhouse_id: 'gh_001' }, query: { at: undefined } },
    })
  })

  it('returns null when there is no state yet (404/no data)', async () => {
    mockedGet.mockResolvedValue({
      data: undefined,
      error: { detail: 'not found' },
      response: new Response(),
    })

    const { result } = renderHook(() => useGreenhouseState('gh_001', null))

    await waitFor(() => expect(mockedGet).toHaveBeenCalled())
    expect(result.current).toBeNull()
  })
})
