import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { apiClient } from '../api/client'
import type { components } from '../../generated/schema'

type GreenhouseListItem = components['schemas']['GreenhouseListItem']

export function GreenhouseListPage() {
  const [greenhouses, setGreenhouses] = useState<GreenhouseListItem[] | null>(null)

  useEffect(() => {
    let cancelled = false
    apiClient.GET('/greenhouses').then(({ data }) => {
      if (!cancelled && data) setGreenhouses(data)
    })
    return () => {
      cancelled = true
    }
  }, [])

  if (greenhouses === null) return <p>Loading greenhouses…</p>

  return (
    <main>
      <h1>Greenhouses</h1>
      <ul>
        {greenhouses.map((greenhouse) => (
          <li key={greenhouse.greenhouse_id}>
            <Link to={`/greenhouses/${greenhouse.greenhouse_id}`}>
              <h2>{greenhouse.name}</h2>
            </Link>
            <p>{greenhouse.crop}</p>
            <p>{greenhouse.plant_count} plants</p>
            <p>{greenhouse.total_steps} simulated days</p>
            <p>Status: {greenhouse.status}</p>
          </li>
        ))}
      </ul>
    </main>
  )
}
