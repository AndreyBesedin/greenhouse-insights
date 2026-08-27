import { useCallback, useEffect, useState } from 'react'

import { apiClient } from '../api/client'
import type { components } from '../../generated/schema'

type SimulationSummary = components['schemas']['SimulationSummary']

const POLL_INTERVAL_MS = 1000

export function useSimulationStatus(simulationId: string, initialStatus: SimulationSummary) {
  const [status, setStatus] = useState(initialStatus)
  const [isPolling, setIsPolling] = useState(initialStatus.status === 'RUNNING')

  const run = useCallback(() => {
    setIsPolling(true)
    void apiClient.POST('/simulations/{simulation_id}/run', {
      params: { path: { simulation_id: simulationId } },
    })
  }, [simulationId])

  useEffect(() => {
    if (!isPolling) return

    const intervalId = setInterval(() => {
      void apiClient
        .GET('/simulations/{simulation_id}/status', {
          params: { path: { simulation_id: simulationId } },
        })
        .then(({ data }) => {
          if (!data) return
          setStatus(data)
          if (data.status === 'COMPLETED' || data.status === 'FAILED') {
            setIsPolling(false)
          }
        })
    }, POLL_INTERVAL_MS)

    return () => clearInterval(intervalId)
  }, [isPolling, simulationId])

  return { status, isPolling, run }
}
