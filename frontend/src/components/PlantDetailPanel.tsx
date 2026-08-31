import { useState } from 'react'

import type { components } from '../../generated/schema'
import { formatMass } from '../lib/format'
import { healthToStatus } from '../lib/status'
import { StatusBadge } from './StatusBadge'

type PlantDetail = components['schemas']['PlantDetail']
type PlantState = components['schemas']['PlantState']

interface PlantDetailPanelProps {
  detail: PlantDetail | null
  history: PlantState[] | null
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

export function PlantDetailPanel({ detail, history }: PlantDetailPanelProps) {
  const [tab, setTab] = useState<'overview' | 'history' | 'raw'>('overview')

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
          <div className="mt-4 flex gap-1 border-b border-white/[0.06] text-xs">
            {(
              [
                ['overview', 'Overview'],
                ['history', 'History'],
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
            <div className="mt-4 grid grid-cols-2 gap-3">
              {state.latest_soil_moisture_pct != null && (
                <MetricTile label="Soil moisture" value={`${state.latest_soil_moisture_pct}%`} />
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
              <MetricTile
                label="Harvested total"
                value={formatMass(state.harvested_total_g)}
                hint="cumulative this cycle"
              />
              {state.last_event_type && (
                <MetricTile label="Last event" value={state.last_event_type} />
              )}
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
