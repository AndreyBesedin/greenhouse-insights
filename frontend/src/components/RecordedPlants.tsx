import { useState } from 'react'

import type { components } from '../../generated/schema'
import { usePlantHistory } from '../hooks/usePlantHistory'
import { formatCheckpoint, formatReading } from '../lib/format'
import { cn } from '../lib/utils'

type Plant = components['schemas']['Plant']
type PlantState = components['schemas']['PlantState']

interface RecordedPlantsProps {
  greenhouseId: string
  /** The plants of the compartment being viewed. */
  plants: Plant[]
  /** Their states in the snapshot being viewed. */
  states: PlantState[]
  /** The checkpoint being viewed: a selected plant's history stops there. */
  upTo: string | null
}

function counts(state: PlantState | undefined) {
  return [
    formatReading(state?.latest_plant_height_cm, 'cm'),
    formatReading(state?.latest_leaf_count, '', 0),
    formatReading(state?.latest_truss_count, '', 0),
    formatReading(state?.latest_open_flower_count, '', 0),
    formatReading(state?.latest_green_fruit_count, '', 0),
    formatReading(state?.latest_coloured_fruit_count, '', 0),
    formatReading(state?.latest_ripe_fruit_count, '', 0),
  ]
}

const COUNT_HEADERS = ['Height', 'Leaves', 'Trusses', 'Flowers', 'Green', 'Coloured', 'Red']

/** One row per measurement: daily snapshots repeat a weekly reading until the
 * next one, so states are collapsed by when the plant was last measured. */
function measurements(history: PlantState[]): PlantState[] {
  const seen = new Set<string>()
  const rows: PlantState[] = []
  for (const state of history) {
    if (!state.last_measured_at || seen.has(state.last_measured_at)) continue
    seen.add(state.last_measured_at)
    rows.push(state)
  }
  return rows
}

/** The manually measured plants of a recorded compartment: their latest
 * readings at the viewed checkpoint, and one plant's measurement history. */
export function RecordedPlants({ greenhouseId, plants, states, upTo }: RecordedPlantsProps) {
  const [selectedPlantId, setSelectedPlantId] = useState<string | null>(null)
  const history = usePlantHistory(greenhouseId, selectedPlantId, upTo)
  const stateById = new Map(states.map((state) => [state.plant_id, state]))
  const ordered = [...plants].sort(
    (a, b) =>
      a.row - b.row ||
      a.position_in_row - b.position_in_row ||
      a.plant_id.localeCompare(b.plant_id),
  )

  return (
    <section className="mt-4 rounded-lg bg-ink-850 p-4 outline-1 -outline-offset-1 outline-white/[0.06]">
      <h3 className="mb-3 text-[11px] font-medium text-mist">
        Measured plants ({plants.length}) · latest readings at this checkpoint
      </h3>
      <div className="overflow-x-auto">
        <table aria-label="Measured plants" className="w-full text-left text-xs">
          <thead className="text-mist">
            <tr>
              <th className="py-1 pr-3 font-normal">Plant</th>
              <th className="py-1 pr-3 font-normal">Treatment</th>
              <th className="py-1 pr-3 font-normal">Last measured</th>
              {COUNT_HEADERS.map((header) => (
                <th key={header} className="py-1 pr-3 font-normal">
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ordered.map((plant) => {
              const state = stateById.get(plant.plant_id)
              const selected = plant.plant_id === selectedPlantId
              return (
                <tr
                  key={plant.plant_id}
                  className={cn('border-t border-white/[0.05]', selected && 'bg-brand/10')}
                >
                  <td className="py-1 pr-3">
                    <button
                      type="button"
                      aria-pressed={selected}
                      onClick={() => setSelectedPlantId(selected ? null : plant.plant_id)}
                      className="text-paper underline-offset-2 hover:underline"
                    >
                      {plant.plant_id}
                    </button>
                  </td>
                  <td className="py-1 pr-3 text-mist">{plant.zone ?? '—'}</td>
                  <td className="py-1 pr-3 text-mist">
                    {state?.last_measured_at ? formatCheckpoint(state.last_measured_at) : '—'}
                  </td>
                  {counts(state).map((value, index) => (
                    <td key={COUNT_HEADERS[index]} className="py-1 pr-3">
                      {value}
                    </td>
                  ))}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {selectedPlantId !== null && (
        <div className="mt-4">
          <h4 className="mb-2 text-[11px] font-medium text-mist">
            {selectedPlantId} · measurements up to this checkpoint
          </h4>
          {history === null ? (
            <p className="text-xs text-mist">Loading history…</p>
          ) : measurements(history).length === 0 ? (
            <p className="text-xs text-mist">No measurements up to this checkpoint.</p>
          ) : (
            <div className="overflow-x-auto">
              <table aria-label="Measurement history" className="w-full text-left text-xs">
                <thead className="text-mist">
                  <tr>
                    <th className="py-1 pr-3 font-normal">Measured</th>
                    {COUNT_HEADERS.map((header) => (
                      <th key={header} className="py-1 pr-3 font-normal">
                        {header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {measurements(history).map((state) => (
                    <tr key={state.last_measured_at} className="border-t border-white/[0.05]">
                      <td className="py-1 pr-3 text-mist">
                        {formatCheckpoint(state.last_measured_at as string)}
                      </td>
                      {counts(state).map((value, index) => (
                        <td key={COUNT_HEADERS[index]} className="py-1 pr-3">
                          {value}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </section>
  )
}
