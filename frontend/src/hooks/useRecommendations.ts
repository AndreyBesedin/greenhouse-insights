import { useEffect, useState } from 'react'

import { apiClient } from '../api/client'
import type { components } from '../../generated/schema'

type Recommendation = components['schemas']['Recommendation']

export function useRecommendations(greenhouseId: string, day: number) {
  const [recommendations, setRecommendations] = useState<Recommendation[] | null>(null)

  useEffect(() => {
    let cancelled = false
    apiClient
      .GET('/greenhouses/{greenhouse_id}/recommendations', {
        params: { path: { greenhouse_id: greenhouseId }, query: { day } },
      })
      .then(({ data }) => {
        if (!cancelled) setRecommendations(data ?? null)
      })
    return () => {
      cancelled = true
    }
  }, [greenhouseId, day])

  async function approve(recommendationId: string) {
    const { data } = await apiClient.POST('/recommendations/{recommendation_id}/approve', {
      params: { path: { recommendation_id: recommendationId } },
    })
    if (data) {
      setRecommendations((current) =>
        (current ?? []).map((r) => (r.recommendation_id === recommendationId ? data : r)),
      )
    }
    return data
  }

  async function dismiss(recommendationId: string) {
    const { data } = await apiClient.POST('/recommendations/{recommendation_id}/dismiss', {
      params: { path: { recommendation_id: recommendationId } },
    })
    if (data) {
      setRecommendations((current) =>
        (current ?? []).map((r) => (r.recommendation_id === recommendationId ? data : r)),
      )
    }
    return data
  }

  return { recommendations, approve, dismiss }
}
