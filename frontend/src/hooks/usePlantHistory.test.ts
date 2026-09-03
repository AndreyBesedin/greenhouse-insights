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

const HISTORY = [
  {
    plant_id: 'plant_017',
    greenhouse_id: 'gh_001',
    simulated_day: 7,
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
  it('returns null when no plant is selected', () => {
    const { result } = renderHook(() => usePlantHistory('gh_001', null, 8))

    expect(result.current).toBeNull()
    expect(mockedGet).not.toHaveBeenCalled()
  })

  it('fetches plant history up to the given day', async () => {
    mockedGet.mockResolvedValue(ok(HISTORY))

    const { result } = renderHook(() => usePlantHistory('gh_001', 'plant_017', 8))

    await waitFor(() => expect(result.current).toEqual(HISTORY))
    expect(mockedGet).toHaveBeenCalledWith(
      '/greenhouses/{greenhouse_id}/plants/{plant_id}/history',
      {
        params: {
          path: { greenhouse_id: 'gh_001', plant_id: 'plant_017' },
          query: { up_to_day: 8 },
        },
      },
    )
  })

  it('refetches when refreshToken changes, without waiting for plant/day to change', async () => {
    const updatedHistory = [...HISTORY, { ...HISTORY[0], simulated_day: 8 }]
    mockedGet.mockResolvedValueOnce(ok(HISTORY)).mockResolvedValueOnce(ok(updatedHistory))

    const { result, rerender } = renderHook(
      ({ token }: { token: number }) => usePlantHistory('gh_001', 'plant_017', 8, token),
      { initialProps: { token: 0 } },
    )
    await waitFor(() => expect(result.current).toEqual(HISTORY))

    rerender({ token: 1 })

    await waitFor(() => expect(result.current).toEqual(updatedHistory))
    expect(mockedGet).toHaveBeenCalledTimes(2)
  })
})
