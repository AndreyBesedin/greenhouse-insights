import { useCallback, useEffect, useState } from 'react'

import { apiClient } from '../api/client'
import type { components } from '../../generated/schema'

type SimulationSummary = components['schemas']['SimulationSummary']

const POLL_INTERVAL_MS = 1000

export function useSimulationStatus(simulationId: string, initialStatus: SimulationSummary) {
  const [status, setStatus] = useState(initialStatus)
  const [isPolling, setIsPolling] = useState(initialStatus.status === 'RUNNING')
  const [isAdvancing, setIsAdvancing] = useState(false)

  const run = useCallback(() => {
    setIsPolling(true)
    void apiClient.POST('/simulations/{simulation_id}/run', {
      params: { path: { simulation_id: simulationId } },
    })
  }, [simulationId])

  const nextDay = useCallback(
    async (confirmDismissRemaining = false) => {
      setIsAdvancing(true)
      const { data, response } = await apiClient.POST('/simulations/{simulation_id}/next-day', {
        params: {
          path: { simulation_id: simulationId },
          query: { confirm_dismiss_remaining: confirmDismissRemaining },
        },
      })
      setIsAdvancing(false)
      if (data) {
        setStatus(data)
        return { blocked: false as const }
      }
      // 409: the current day still has PENDING recommendations - the caller
      // decides whether to show a confirm-and-dismiss prompt and retry with
      // confirmDismissRemaining=true.
      return { blocked: response.status === 409 }
    },
    [simulationId],
  )

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

  return { status, isPolling, isAdvancing, run, nextDay }
}
