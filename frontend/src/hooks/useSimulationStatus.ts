import { useCallback, useEffect, useState } from 'react'

import { apiClient } from '../api/client'
import type { components } from '../../generated/schema'

type SimulationSummary = components['schemas']['SimulationSummary']
type ManagementProgress = components['schemas']['ManagementProgress']

const POLL_INTERVAL_MS = 1000
const PROGRESS_POLL_INTERVAL_MS = 500

export function useSimulationStatus(simulationId: string, initialStatus: SimulationSummary) {
  const [status, setStatus] = useState(initialStatus)
  const [isPolling, setIsPolling] = useState(initialStatus.status === 'RUNNING')
  const [isAdvancing, setIsAdvancing] = useState(false)
  const [analysisProgress, setAnalysisProgress] = useState<ManagementProgress | null>(null)

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
      setAnalysisProgress(null)
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

  useEffect(() => {
    if (!isAdvancing) return

    const intervalId = setInterval(() => {
      void apiClient
        .GET('/simulations/{simulation_id}/management-progress', {
          params: { path: { simulation_id: simulationId } },
        })
        .then(({ data }) => setAnalysisProgress(data ?? null))
    }, PROGRESS_POLL_INTERVAL_MS)

    return () => clearInterval(intervalId)
  }, [isAdvancing, simulationId])

  return { status, isPolling, isAdvancing, analysisProgress, run, nextDay }
}
