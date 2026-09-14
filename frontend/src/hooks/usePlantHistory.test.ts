import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '../api/client'
import { usePlantHistory } from './usePlantHistory'

vi.mock('../api/client', () => ({
  apiClient: { GET: vi.fn() },
}))

const mockedGet = vi.mocked(apiClient.GET)

function ok<T>(data: T) {
  return { data, error: undefined, response: new Response() }
}

const AT_8 = '2026-01-08T00:00:00+00:00'

const HISTORY = [
  {
    plant_id: 'plant_017',
    greenhouse_id: 'gh_001',
    timestamp: '2026-01-08T00:00:00Z',
    health: 'HEALTHY',
    latest_soil_moisture_pct: 40,
    latest_visible_fruit_count: 30,
    latest_ripe_fruit_count: 4,
    last_event_type: null,
    last_event_timestamp: null,
    provenance: 'DETERMINISTICALLY_DERIVED',
  },
]

beforeEach(() => {
  mockedGet.mockReset()
})

describe('usePlantHistory', () => {
  it('is empty without fetching when no checkpoint exists yet', async () => {
    const { result } = renderHook(() => usePlantHistory('gh_001', 'plant_017', null))

    await waitFor(() => expect(result.current).toEqual([]))
    expect(mockedGet).not.toHaveBeenCalled()
  })

  it('returns null when no plant is selected', () => {
    const { result } = renderHook(() => usePlantHistory('gh_001', null, AT_8))

    expect(result.current).toBeNull()
    expect(mockedGet).not.toHaveBeenCalled()
  })

  it('fetches plant history up to the given instant', async () => {
    mockedGet.mockResolvedValue(ok(HISTORY))

    const { result } = renderHook(() => usePlantHistory('gh_001', 'plant_017', AT_8))

    await waitFor(() => expect(result.current).toEqual(HISTORY))
    expect(mockedGet).toHaveBeenCalledWith(
      '/greenhouses/{greenhouse_id}/plants/{plant_id}/history',
      {
        params: {
          path: { greenhouse_id: 'gh_001', plant_id: 'plant_017' },
          query: { up_to: AT_8 },
        },
      },
    )
  })

  it('refetches when refreshToken changes, without waiting for plant/instant to change', async () => {
    const updatedHistory = [...HISTORY, { ...HISTORY[0], timestamp: AT_8 }]
    mockedGet.mockResolvedValueOnce(ok(HISTORY)).mockResolvedValueOnce(ok(updatedHistory))

    const { result, rerender } = renderHook(
      ({ token }: { token: number }) => usePlantHistory('gh_001', 'plant_017', AT_8, token),
      { initialProps: { token: 0 } },
    )
    await waitFor(() => expect(result.current).toEqual(HISTORY))

    rerender({ token: 1 })

    await waitFor(() => expect(result.current).toEqual(updatedHistory))
    expect(mockedGet).toHaveBeenCalledTimes(2)
  })
})
