import type { components } from '../../generated/schema'
import { healthToStatus, STATUS_META } from '../lib/status'
import { PlantMarker } from './PlantMarker'

type Plant = components['schemas']['Plant']
type PlantHealth = components['schemas']['PlantState']['health']

interface GreenhouseMapProps {
  plants: Plant[]
  healthByPlantId: Map<string, PlantHealth>
  selectedPlantId: string | null
  onSelectPlant: (plantId: string) => void
}

const LEGEND_STATUSES = ['healthy', 'monitor', 'action-required'] as const

export function GreenhouseMap({
  plants,
  healthByPlantId,
  selectedPlantId,
  onSelectPlant,
}: GreenhouseMapProps) {
  const rows = new Map<number, Plant[]>()
  for (const plant of plants) {
    const row = rows.get(plant.row) ?? []
    row.push(plant)
    rows.set(plant.row, row)
  }
  for (const row of rows.values()) {
    row.sort((a, b) => a.position_in_row - b.position_in_row)
  }

  return (
    <div role="grid">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-display text-sm font-medium tracking-tight">Plant map · top-down</h2>
        <div className="flex items-center gap-4 text-[11px] text-mist">
          {LEGEND_STATUSES.map((status) => (
            <span key={status} className="inline-flex items-center gap-1.5">
              <span className={`size-2 rounded-full ${STATUS_META[status].dot}`} />
              {STATUS_META[status].label}
            </span>
          ))}
        </div>
      </div>

      <div className="space-y-3">
        {[...rows.entries()].map(([rowIndex, rowPlants]) => (
          <div key={rowIndex} className="flex items-center gap-2">
            <span className="w-6 text-[10px] text-mist">{rowIndex}</span>
            <div className="flex flex-1 flex-wrap gap-3">
              {rowPlants.map((plant) => {
                const health = healthByPlantId.get(plant.plant_id) ?? 'UNKNOWN'
                return (
                  <PlantMarker
                    key={plant.plant_id}
                    plantId={plant.plant_id}
                    row={plant.row}
                    positionInRow={plant.position_in_row}
                    crop={plant.variety}
                    status={healthToStatus(health)}
                    health={health}
                    selected={plant.plant_id === selectedPlantId}
                    onSelect={onSelectPlant}
                  />
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
