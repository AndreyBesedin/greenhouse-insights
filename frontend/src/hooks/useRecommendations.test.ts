import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '../api/client'
import { useRecommendations } from './useRecommendations'

vi.mock('../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn() },
}))

const mockedGet = vi.mocked(apiClient.GET)
const mockedPost = vi.mocked(apiClient.POST)

function ok<T>(data: T) {
  return { data, error: undefined, response: new Response() }
}

const AT_2 = '2026-01-02T00:00:00+00:00'

const PENDING = {
  recommendation_id: 'rec_1',
  source: { type: 'SIMULATION', source_id: 'sim_gh_001' },
  greenhouse_id: 'gh_001',
  context_timestamp: AT_2,
  plant_id: 'plant_017',
  action: { action_type: 'WATER_PLANT', plant_id: 'plant_017', amount_ml: 700 },
  source_policy: 'DETERMINISTIC',
  status: 'PENDING',
  reason: 'Soil moisture at 37%.',
  evidence: { soil_moisture_pct: 37 },
  rejection_reason: null,
  approved_by: null,
  executed_by: null,
  requested_at: '2026-01-02T00:00:00Z',
  reviewed_at: null,
  executed_at: null,
} as const

beforeEach(() => {
  mockedGet.mockReset()
  mockedPost.mockReset()
})

describe('useRecommendations', () => {
  it('fetches recommendations for the given greenhouse and instant', async () => {
    mockedGet.mockResolvedValue(ok([PENDING]))

    const { result } = renderHook(() => useRecommendations('gh_001', AT_2))

    await waitFor(() => expect(result.current.recommendations).toEqual([PENDING]))
    expect(mockedGet).toHaveBeenCalledWith('/greenhouses/{greenhouse_id}/recommendations', {
      params: { path: { greenhouse_id: 'gh_001' }, query: { at: AT_2 } },
    })
  })

  it('approve replaces the recommendation with the returned executed version', async () => {
    mockedGet.mockResolvedValue(ok([PENDING]))
    const executed = { ...PENDING, status: 'EXECUTED', approved_by: 'HUMAN' } as const
    mockedPost.mockResolvedValue(ok(executed))

    const { result } = renderHook(() => useRecommendations('gh_001', AT_2))
    await waitFor(() => expect(result.current.recommendations).toEqual([PENDING]))

    await act(async () => {
      await result.current.approve('rec_1')
    })

    expect(mockedPost).toHaveBeenCalledWith('/recommendations/{recommendation_id}/approve', {
      params: { path: { recommendation_id: 'rec_1' } },
    })
    expect(result.current.recommendations).toEqual([executed])
  })

  it('dismiss replaces the recommendation with the returned dismissed version', async () => {
    mockedGet.mockResolvedValue(ok([PENDING]))
    const dismissed = { ...PENDING, status: 'DISMISSED' } as const
    mockedPost.mockResolvedValue(ok(dismissed))

    const { result } = renderHook(() => useRecommendations('gh_001', AT_2))
    await waitFor(() => expect(result.current.recommendations).toEqual([PENDING]))

    await act(async () => {
      await result.current.dismiss('rec_1')
    })

    expect(mockedPost).toHaveBeenCalledWith('/recommendations/{recommendation_id}/dismiss', {
      params: { path: { recommendation_id: 'rec_1' } },
    })
    expect(result.current.recommendations).toEqual([dismissed])
  })
})
