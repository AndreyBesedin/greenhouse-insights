import type { components } from '../../generated/schema'

type Plant = components['schemas']['Plant']
type PlantHealth = components['schemas']['PlantState']['health']

interface GreenhouseMapProps {
  plants: Plant[]
  healthByPlantId: Map<string, PlantHealth>
  selectedPlantId: string | null
  onSelectPlant: (plantId: string) => void
}

export function GreenhouseMap({
  plants,
  healthByPlantId,
  selectedPlantId,
  onSelectPlant,
}: GreenhouseMapProps) {
  const rows = Math.max(1, ...plants.map((plant) => plant.row))
  const columns = Math.max(1, ...plants.map((plant) => plant.position_in_row))

  return (
    <div
      role="grid"
      style={{
        display: 'grid',
        gridTemplateRows: `repeat(${rows}, auto)`,
        gridTemplateColumns: `repeat(${columns}, auto)`,
        gap: '0.5rem',
      }}
    >
      {plants.map((plant) => {
        const health = healthByPlantId.get(plant.plant_id) ?? 'UNKNOWN'
        const isSelected = plant.plant_id === selectedPlantId
        return (
          <button
            key={plant.plant_id}
            type="button"
            data-health={health}
            aria-pressed={isSelected}
            style={{ gridRow: plant.row, gridColumn: plant.position_in_row }}
            onClick={() => onSelectPlant(plant.plant_id)}
          >
            {plant.plant_id}
          </button>
        )
      })}
    </div>
  )
}
