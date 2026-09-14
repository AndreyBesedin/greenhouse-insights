import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '../api/client'
import { usePlantDetail } from './usePlantDetail'

vi.mock('../api/client', () => ({
  apiClient: { GET: vi.fn() },
}))

const mockedGet = vi.mocked(apiClient.GET)

function ok<T>(data: T) {
  return { data, error: undefined, response: new Response() }
}

const AT_1 = '2026-01-01T00:00:00+00:00'

const DETAIL = {
  plant: { plant_id: 'plant_017', variety: 'cherry_tomato', row: 2, position_in_row: 7 },
  state: null,
}

beforeEach(() => {
  mockedGet.mockReset()
})

describe('usePlantDetail', () => {
  it('returns null when no plant is selected', () => {
    const { result } = renderHook(() => usePlantDetail('gh_001', null, AT_1))

    expect(result.current).toBeNull()
    expect(mockedGet).not.toHaveBeenCalled()
  })

  it('fetches plant detail for the given plant and instant', async () => {
    mockedGet.mockResolvedValue(ok(DETAIL))

    const { result } = renderHook(() => usePlantDetail('gh_001', 'plant_017', AT_1))

    await waitFor(() => expect(result.current).toEqual(DETAIL))
    expect(mockedGet).toHaveBeenCalledWith('/greenhouses/{greenhouse_id}/plants/{plant_id}', {
      params: { path: { greenhouse_id: 'gh_001', plant_id: 'plant_017' }, query: { at: AT_1 } },
    })
  })

  it('refetches when refreshToken changes, without waiting for plant/instant to change', async () => {
    const updated = { ...DETAIL, state: { health: 'MONITOR' } }
    mockedGet.mockResolvedValueOnce(ok(DETAIL)).mockResolvedValueOnce(ok(updated))

    const { result, rerender } = renderHook(
      ({ token }: { token: number }) => usePlantDetail('gh_001', 'plant_017', AT_1, token),
      { initialProps: { token: 0 } },
    )
    await waitFor(() => expect(result.current).toEqual(DETAIL))

    rerender({ token: 1 })

    await waitFor(() => expect(result.current).toEqual(updated))
    expect(mockedGet).toHaveBeenCalledTimes(2)
  })
})
