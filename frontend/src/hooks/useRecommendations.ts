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

  // Appends a recommendation created outside the normal propose/review flow
  // (a manual action) without a refetch - mirrors approve/dismiss patching
  // from the response they already have rather than re-fetching the list.
  function add(recommendation: Recommendation) {
    setRecommendations((current) => [...(current ?? []), recommendation])
  }

  async function approveAll() {
    const { data } = await apiClient.POST(
      '/greenhouses/{greenhouse_id}/recommendations/approve-all',
      {
        params: { path: { greenhouse_id: greenhouseId }, query: { day } },
      },
    )
    if (data) {
      const byId = new Map(data.map((r) => [r.recommendation_id, r]))
      setRecommendations((current) =>
        (current ?? []).map((r) => byId.get(r.recommendation_id) ?? r),
      )
    }
    return data
  }

  return { recommendations, approve, dismiss, add, approveAll }
}
