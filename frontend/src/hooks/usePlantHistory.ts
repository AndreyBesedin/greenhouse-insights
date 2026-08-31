import { useEffect, useState } from 'react'

import { apiClient } from '../api/client'
import type { components } from '../../generated/schema'

type PlantState = components['schemas']['PlantState']

export function usePlantHistory(
  greenhouseId: string,
  plantId: string | null,
  upToDay: number,
): PlantState[] | null {
  const [history, setHistory] = useState<PlantState[] | null>(null)

  useEffect(() => {
    if (plantId === null) return
    let cancelled = false
    apiClient
      .GET('/greenhouses/{greenhouse_id}/plants/{plant_id}/history', {
        params: {
          path: { greenhouse_id: greenhouseId, plant_id: plantId },
          query: { up_to_day: upToDay },
        },
      })
      .then(({ data }) => {
        if (!cancelled) setHistory(data ?? null)
      })
    return () => {
      cancelled = true
    }
  }, [greenhouseId, plantId, upToDay])

  return plantId === null ? null : history
}
