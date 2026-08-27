import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { apiClient } from '../api/client'
import { useSimulationStatus } from '../hooks/useSimulationStatus'
import type { components } from '../../generated/schema'

type GreenhouseDetail = components['schemas']['GreenhouseDetail']

export function GreenhouseDashboardPage() {
  const { greenhouseId } = useParams<{ greenhouseId: string }>()
  const [detail, setDetail] = useState<GreenhouseDetail | null>(null)

  useEffect(() => {
    if (!greenhouseId) return
    let cancelled = false
    apiClient
      .GET('/greenhouses/{greenhouse_id}', { params: { path: { greenhouse_id: greenhouseId } } })
      .then(({ data }) => {
        if (!cancelled && data) setDetail(data)
      })
    return () => {
      cancelled = true
    }
  }, [greenhouseId])

  if (detail === null) return <p>Loading greenhouse…</p>

  return <DashboardContent detail={detail} />
}

function DashboardContent({ detail }: { detail: GreenhouseDetail }) {
  const { greenhouse, simulation } = detail
  const { status, isPolling, run } = useSimulationStatus(simulation.simulation_id, simulation)
  const isFinished = status.status === 'COMPLETED' || status.status === 'FAILED'

  return (
    <main>
      <Link to="/">← Greenhouses</Link>
      <h1>{greenhouse.name}</h1>
      <p>{`Day ${status.current_step} / ${status.total_steps}`}</p>
      <progress value={status.current_step} max={status.total_steps} />
      <button type="button" onClick={run} disabled={isPolling || isFinished}>
        Run Simulation
      </button>
    </main>
  )
}
