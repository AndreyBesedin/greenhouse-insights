import { useState } from 'react'

import type { components } from '../../generated/schema'
import { cropIconVariant } from '../lib/crop'
import { formatMass } from '../lib/format'
import { healthToStatus } from '../lib/status'
import { CropIcon } from './CropIcon'
import { StatusBadge } from './StatusBadge'

type PlantDetail = components['schemas']['PlantDetail']
type PlantState = components['schemas']['PlantState']
type Recommendation = components['schemas']['Recommendation']

export type RequestedAction =
  | components['schemas']['WaterPlantAction']
  | components['schemas']['HarvestPlantAction']
  | components['schemas']['LowerPlantAction']
  | components['schemas']['ScheduleInspectionAction']

const DEFAULT_WATER_ML = 700
const DEFAULT_LOWER_CM = 40

interface PlantDetailPanelProps {
  detail: PlantDetail | null
  history: PlantState[] | null
  /** Every recommendation for the day currently being viewed - used to spot
   * whether this plant already has one, and to explain when it doesn't. */
  recommendations: Recommendation[] | null
  /** True only when viewing the current day - manual actions, like
   * recommendation review, only make sense on "today". */
  interactive: boolean
  isSubmittingAction: boolean
  onSubmitAction: (action: RequestedAction) => void
}

function MetricTile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-md bg-ink-800 p-3 outline-1 -outline-offset-1 outline-white/[0.05]">
      <div className="text-[11px] text-mist">{label}</div>
      <div className="mt-1 font-display text-lg font-medium">{value}</div>
      {hint && <div className="mt-1.5 text-[11px] text-mist">{hint}</div>}
    </div>
  )
}

export function PlantDetailPanel({
  detail,
  history,
  recommendations,
  interactive,
  isSubmittingAction,
  onSubmitAction,
}: PlantDetailPanelProps) {
  const [tab, setTab] = useState<'overview' | 'history' | 'acquisitions' | 'raw'>('overview')

  if (detail === null) {
    return (
      <aside className="grid place-items-center rounded-lg bg-ink-850 p-10 text-center outline-1 -outline-offset-1 outline-white/[0.06]">
        <p className="text-xs text-mist">
          Select a plant to inspect its current state and history.
        </p>
      </aside>
    )
  }

  const { plant, state } = detail
  const hasRecommendationToday = (recommendations ?? []).some((r) => r.plant_id === plant.plant_id)
  const needsAttention = state != null && state.health !== 'HEALTHY'

  return (
    <aside className="rounded-lg bg-ink-850 p-5 outline-1 -outline-offset-1 outline-white/[0.06]">
      <div className="flex items-center justify-between">
        <div>
          <div className="font-display text-sm font-medium">{plant.plant_id}</div>
          <div className="text-[11px] text-mist">{`Row ${plant.row} · Position ${plant.position_in_row}`}</div>
        </div>
        {state && <StatusBadge status={healthToStatus(state.health)} />}
      </div>

      {state === null ? (
        <p className="mt-4 text-xs text-mist">No observations yet.</p>
      ) : (
        <>
          {needsAttention && (
            <div className="mt-3 rounded-md bg-amber/[0.08] px-3 py-2 text-[11px] text-paper outline-1 -outline-offset-1 outline-amber/30">
              <p className="text-mist">
                {hasRecommendationToday
                  ? 'The AI assistant has a recommendation for this plant today - see below.'
                  : 'No AI recommendation for this plant today - use quick actions to act directly.'}
              </p>
            </div>
          )}

          {interactive && (
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                disabled={isSubmittingAction}
                onClick={() =>
                  onSubmitAction({
                    action_type: 'WATER_PLANT',
                    plant_id: plant.plant_id,
                    amount_ml: DEFAULT_WATER_ML,
                  })
                }
                className="rounded-md bg-ink-700 px-2.5 py-1.5 text-xs font-medium text-paper transition-colors hover:bg-ink-600 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Water {DEFAULT_WATER_ML} ml
              </button>
              <button
                type="button"
                disabled={isSubmittingAction}
                onClick={() =>
                  onSubmitAction({ action_type: 'HARVEST_PLANT', plant_id: plant.plant_id })
                }
                className="rounded-md bg-ink-700 px-2.5 py-1.5 text-xs font-medium text-paper transition-colors hover:bg-ink-600 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Harvest ripe fruit
              </button>
              <button
                type="button"
                disabled={isSubmittingAction}
                onClick={() =>
                  onSubmitAction({
                    action_type: 'LOWER_PLANT',
                    plant_id: plant.plant_id,
                    amount_cm: DEFAULT_LOWER_CM,
                  })
                }
                className="rounded-md bg-ink-700 px-2.5 py-1.5 text-xs font-medium text-paper transition-colors hover:bg-ink-600 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Lower {DEFAULT_LOWER_CM} cm
              </button>
              <button
                type="button"
                disabled={isSubmittingAction}
                onClick={() =>
                  onSubmitAction({
                    action_type: 'SCHEDULE_INSPECTION',
                    plant_id: plant.plant_id,
                    reason: 'Manually requested by operator.',
                  })
                }
                className="rounded-md bg-ink-700 px-2.5 py-1.5 text-xs font-medium text-paper transition-colors hover:bg-ink-600 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Schedule inspection
              </button>
            </div>
          )}

          <div className="mt-4 flex gap-1 border-b border-white/[0.06] text-xs">
            {(
              [
                ['overview', 'Overview'],
                ['history', 'History'],
                ['acquisitions', 'Acquisitions'],
                ['raw', 'Raw state'],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => setTab(key)}
                className={`-mb-px cursor-pointer border-b pb-2 pl-1 pr-3 transition-colors ${
                  tab === key
                    ? 'border-brand font-medium text-paper'
                    : 'border-transparent text-mist hover:text-paper'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {tab === 'overview' && (
            <div className="mt-4 space-y-4">
              <div>
                <h3 className="text-[11px] font-medium text-mist">Today's sensor reading</h3>
                <p className="mt-0.5 text-[10px] text-mist/70">
                  Taken once per simulated day - an action approved today will not move these until
                  tomorrow's reading.
                </p>
                <div className="mt-2 grid grid-cols-2 gap-3">
                  {state.latest_soil_moisture_pct != null && (
                    <MetricTile
                      label="Soil moisture"
                      value={`${state.latest_soil_moisture_pct}%`}
                    />
                  )}
                  {state.latest_visible_fruit_count != null && (
                    <MetricTile
                      label="Visible fruit"
                      value={String(state.latest_visible_fruit_count)}
                      hint={
                        state.latest_ripe_fruit_count != null
                          ? `${state.latest_ripe_fruit_count} ripe`
                          : undefined
                      }
                    />
                  )}
                  {state.latest_estimated_ripe_mass_g != null && (
                    <MetricTile
                      label="Ripe mass"
                      value={formatMass(state.latest_estimated_ripe_mass_g)}
                      hint="ready to harvest"
                    />
                  )}
                </div>
              </div>

              <div>
                <h3 className="text-[11px] font-medium text-mist">Updates immediately</h3>
                <div className="mt-2 grid grid-cols-2 gap-3">
                  <MetricTile
                    label="Harvested total"
                    value={formatMass(state.harvested_total_g)}
                    hint="cumulative this cycle"
                  />
                  {state.last_event_type && (
                    <MetricTile label="Last event" value={state.last_event_type} />
                  )}
                </div>
              </div>
            </div>
          )}

          {tab === 'history' && (
            <div className="mt-4 space-y-3">
              {history === null && <div className="text-xs text-mist">Loading history…</div>}
              {history !== null && history.length === 0 && (
                <div className="text-xs text-mist">No history yet.</div>
              )}
              {history?.map((entry, index) => (
                <div key={index} className="flex gap-3">
                  <span className="mt-1 size-1.5 shrink-0 rounded-full bg-brand" aria-hidden />
                  <div className="text-xs">
                    <span className="text-paper">Day {entry.simulated_day}</span>{' '}
                    <span className="text-mist">
                      — {entry.health}
                      {entry.last_event_type ? ` · ${entry.last_event_type}` : ''}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {tab === 'acquisitions' && (
            <div className="mt-4 grid place-items-center rounded-md bg-ink-800 p-8 text-center outline-1 -outline-offset-1 outline-white/[0.05]">
              <CropIcon crop={cropIconVariant(plant.variety)} size="xl" className="text-mist" />
              <p className="mt-3 text-xs text-paper">No image acquisitions yet.</p>
              <p className="mt-1 text-[11px] text-mist">
                Vision captures will appear here once a camera feed is connected.
              </p>
            </div>
          )}

          {tab === 'raw' && (
            <pre className="mt-4 overflow-x-auto rounded-md bg-ink-900 p-3.5 font-mono text-[11px] leading-relaxed text-mist outline-1 -outline-offset-1 outline-white/[0.05]">
              {JSON.stringify(state, null, 2)}
            </pre>
          )}
        </>
      )}
    </aside>
  )
}
