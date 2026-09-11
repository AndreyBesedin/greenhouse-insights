import { useEffect, useState } from 'react'

import { apiClient } from '../api/client'
import type { components } from '../../generated/schema'

type PlantDetail = components['schemas']['PlantDetail']

export function usePlantDetail(
  greenhouseId: string,
  plantId: string | null,
  // See useGreenhouseState: the instant to view the plant at, null = latest.
  at: string | null,
  // Bump this (e.g. after approving a recommendation or submitting a manual
  // action, either of which can change this plant's state) to force a
  // refetch without waiting for greenhouseId/plantId/at to change - mirrors
  // useGreenhouseState's refreshToken.
  refreshToken: number = 0,
): PlantDetail | null {
  const [detail, setDetail] = useState<PlantDetail | null>(null)

  useEffect(() => {
    if (plantId === null) return
    let cancelled = false
    apiClient
      .GET('/greenhouses/{greenhouse_id}/plants/{plant_id}', {
        params: {
          path: { greenhouse_id: greenhouseId, plant_id: plantId },
          query: { at: at ?? undefined },
        },
      })
      .then(({ data }) => {
        if (!cancelled) setDetail(data ?? null)
      })
    return () => {
      cancelled = true
    }
  }, [greenhouseId, plantId, at, refreshToken])

  return plantId === null ? null : detail
}
