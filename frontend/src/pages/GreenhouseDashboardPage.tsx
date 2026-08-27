import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { apiClient } from '../api/client'
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

  const { greenhouse, simulation } = detail

  return (
    <main>
      <Link to="/">← Greenhouses</Link>
      <h1>{greenhouse.name}</h1>
      <p>
        Day {simulation.current_step} / {simulation.total_steps}
      </p>
      <button type="button" disabled>
        Run Simulation
      </button>
    </main>
  )
}
