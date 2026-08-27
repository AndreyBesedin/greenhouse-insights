import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { apiClient } from '../api/client'
import { DayNavigator } from '../components/DayNavigator'
import { GreenhouseMap } from '../components/GreenhouseMap'
import { PlantDetailPanel } from '../components/PlantDetailPanel'
import { useGreenhouseState } from '../hooks/useGreenhouseState'
import { usePlantDetail } from '../hooks/usePlantDetail'
import { useSimulationStatus } from '../hooks/useSimulationStatus'
import type { components } from '../../generated/schema'

type GreenhouseDetail = components['schemas']['GreenhouseDetail']
type PlantHealth = components['schemas']['PlantState']['health']

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

  const [selectedPlantId, setSelectedPlantId] = useState<string | null>(null)
  const [manualViewingDay, setManualViewingDay] = useState<number | null>(null)
  const viewingDay = manualViewingDay ?? status.current_step

  const state = useGreenhouseState(greenhouse.greenhouse_id, viewingDay)
  const plantDetail = usePlantDetail(greenhouse.greenhouse_id, selectedPlantId, viewingDay)

  const healthByPlantId = new Map<string, PlantHealth>(
    (state?.plant_states ?? []).map((plantState) => [plantState.plant_id, plantState.health]),
  )

  return (
    <main>
      <Link to="/">← Greenhouses</Link>
      <h1>{greenhouse.name}</h1>
      <p>{`Day ${status.current_step} / ${status.total_steps}`}</p>
      <progress value={status.current_step} max={status.total_steps} />
      <button type="button" onClick={run} disabled={isPolling || isFinished}>
        Run Simulation
      </button>

      <p>
        {`${state?.plants_healthy ?? 0} healthy | ${state?.plants_monitor ?? 0} monitor | ` +
          `${state?.plants_action_required ?? 0} action required`}
      </p>

      <DayNavigator
        viewingDay={viewingDay}
        currentDay={status.current_step}
        totalDays={status.total_steps}
        isFinished={isFinished}
        onSelectDay={setManualViewingDay}
        onReturnToCurrent={() => setManualViewingDay(null)}
      />

      <GreenhouseMap
        plants={greenhouse.plants}
        healthByPlantId={healthByPlantId}
        selectedPlantId={selectedPlantId}
        onSelectPlant={setSelectedPlantId}
      />
      <PlantDetailPanel detail={plantDetail} />
    </main>
  )
}
