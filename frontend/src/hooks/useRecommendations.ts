import { useEffect, useState } from 'react'

import { apiClient } from '../api/client'
import type { components } from '../../generated/schema'

type Recommendation = components['schemas']['Recommendation']

// at: the ISO-8601 instant of the state snapshot being viewed - a
// recommendation belongs to the snapshot it was made against. null means no
// snapshot exists yet, so there is nothing to fetch.
export function useRecommendations(greenhouseId: string, at: string | null) {
  const [recommendations, setRecommendations] = useState<Recommendation[] | null>(null)

  useEffect(() => {
    if (at === null) return
    let cancelled = false
    apiClient
      .GET('/greenhouses/{greenhouse_id}/recommendations', {
        params: { path: { greenhouse_id: greenhouseId }, query: { at } },
      })
      .then(({ data }) => {
        if (!cancelled) setRecommendations(data ?? null)
      })
    return () => {
      cancelled = true
    }
  }, [greenhouseId, at])

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
    if (at === null) return []
    const { data } = await apiClient.POST(
      '/greenhouses/{greenhouse_id}/recommendations/approve-all',
      {
        params: { path: { greenhouse_id: greenhouseId }, query: { at } },
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

  return { recommendations: at === null ? [] : recommendations, approve, dismiss, add, approveAll }
}
