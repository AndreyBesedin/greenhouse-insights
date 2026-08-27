import { useEffect, useState } from 'react'

import { apiClient } from '../api/client'
import type { components } from '../../generated/schema'

type GreenhouseState = components['schemas']['GreenhouseState']

export function useGreenhouseState(greenhouseId: string, day: number): GreenhouseState | null {
  const [state, setState] = useState<GreenhouseState | null>(null)

  useEffect(() => {
    let cancelled = false
    apiClient
      .GET('/greenhouses/{greenhouse_id}/state', {
        params: { path: { greenhouse_id: greenhouseId }, query: { day } },
      })
      .then(({ data }) => {
        if (!cancelled) setState(data ?? null)
      })
    return () => {
      cancelled = true
    }
  }, [greenhouseId, day])

  return state
}
