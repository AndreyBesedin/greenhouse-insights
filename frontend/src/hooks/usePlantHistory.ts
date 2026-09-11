import { useEffect, useState } from 'react'

import { apiClient } from '../api/client'
import type { components } from '../../generated/schema'

type PlantState = components['schemas']['PlantState']

export function usePlantHistory(
  greenhouseId: string,
  plantId: string | null,
  // ISO-8601 instant: every state snapshot taken at or before it. null
  // means no checkpoint exists yet, so there is no history to fetch.
  upTo: string | null,
  // See usePlantDetail's refreshToken.
  refreshToken: number = 0,
): PlantState[] | null {
  const [history, setHistory] = useState<PlantState[] | null>(null)

  useEffect(() => {
    if (plantId === null || upTo === null) return
    let cancelled = false
    apiClient
      .GET('/greenhouses/{greenhouse_id}/plants/{plant_id}/history', {
        params: {
          path: { greenhouse_id: greenhouseId, plant_id: plantId },
          query: { up_to: upTo },
        },
      })
      .then(({ data }) => {
        if (!cancelled) setHistory(data ?? null)
      })
    return () => {
      cancelled = true
    }
  }, [greenhouseId, plantId, upTo, refreshToken])

  if (plantId === null) return null
  return upTo === null ? [] : history
}
