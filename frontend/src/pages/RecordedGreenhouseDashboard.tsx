import { useState } from 'react'
import { Link } from 'react-router-dom'

import { AppShell } from '../components/AppShell'
import { DayNavigator } from '../components/DayNavigator'
import { useGreenhouseState } from '../hooks/useGreenhouseState'
import { useTimeline } from '../hooks/useTimeline'
import { cn } from '../lib/utils'
import { formatCheckpoint, formatCropLabel, formatMass, formatReading } from '../lib/format'
import type { components } from '../../generated/schema'

type GreenhouseDetail = components['schemas']['GreenhouseDetail']
type Environment = components['schemas']['GreenhouseEnvironmentState']

function Tile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-lg bg-ink-850 p-4 outline-1 -outline-offset-1 outline-white/[0.06]">
      <div className="text-xs text-mist">{label}</div>
      <div className="mt-1.5 font-display text-2xl font-medium">{value}</div>
      {hint && <div className="mt-1 text-[11px] text-mist">{hint}</div>}
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 text-xs">
      <span className="text-mist">{label}</span>
      <span className="text-paper">{value}</span>
    </div>
  )
}

function ControlPanel({ title, rows }: { title: string; rows: [string, string][] }) {
  return (
    <section className="rounded-lg bg-ink-850 p-4 outline-1 -outline-offset-1 outline-white/[0.06]">
      <h3 className="mb-3 text-[11px] font-medium text-mist">{title}</h3>
      <div className="space-y-2">
        {rows.map(([label, value]) => (
          <Row key={label} label={label} value={value} />
        ))}
      </div>
    </section>
  )
}

/** A greenhouse whose observation history was imported from a recorded
 * dataset. The timeline is real recorded time; nothing here can change it -
 * a recorded history is not a simulator.
 *
 * A greenhouse with compartments (each with its own climate and control)
 * shows one compartment at a time; one without shows its greenhouse-level
 * readings. */
export function RecordedGreenhouseDashboard({ detail }: { detail: GreenhouseDetail }) {
  const { greenhouse } = detail
  const crop = greenhouse.crop ?? 'tomato'
  const compartments = greenhouse.compartments ?? []
  const { checkpoints } = useTimeline(greenhouse.greenhouse_id, 0)
  const latestIndex = checkpoints.length
  const [manualViewingIndex, setManualViewingIndex] = useState<number | null>(null)
  const [selectedCompartmentId, setSelectedCompartmentId] = useState<string | null>(null)
  const viewingIndex = manualViewingIndex ?? latestIndex
  const viewingAt = checkpoints[viewingIndex - 1] ?? null
  const state = useGreenhouseState(greenhouse.greenhouse_id, viewingAt)

  const activeCompartmentId = selectedCompartmentId ?? compartments[0]?.compartment_id ?? null
  const activeCompartment = compartments.find((c) => c.compartment_id === activeCompartmentId)
  const compartmentState =
    activeCompartmentId === null
      ? null
      : (state?.compartments?.find((c) => c.compartment_id === activeCompartmentId) ?? null)
  const environment: Environment =
    activeCompartmentId === null
      ? (state?.environment ?? {})
      : (compartmentState?.environment ?? {})
  const harvestedG =
    activeCompartmentId === null
      ? (state?.total_harvested_g ?? 0)
      : (compartmentState?.harvested_total_g ?? 0)
  const costParts = [
    environment.heating_cost_today_eur_m2,
    environment.lighting_cost_today_eur_m2,
    environment.co2_cost_today_eur_m2,
    environment.fixed_cost_today_eur_m2,
  ].filter((value): value is number => value !== null && value !== undefined)
  const costsToday =
    costParts.length === 0 ? '—' : `€${costParts.reduce((sum, value) => sum + value, 0).toFixed(3)}`

  const formatDay = (index: number) => {
    const checkpoint = checkpoints[index - 1]
    return checkpoint ? formatCheckpoint(checkpoint) : `Checkpoint ${index}`
  }

  return (
    <AppShell>
      <main className="mx-auto max-w-[1440px] px-6 py-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="mb-2 text-xs text-mist">
              <Link to="/" className="transition-colors hover:text-paper">
                ← Greenhouses
              </Link>
              <span className="mx-1 opacity-50">/</span>
              <span className="text-paper">{greenhouse.name}</span>
            </div>
            <div className="flex flex-wrap items-center gap-4">
              <h1 className="max-w-[40ch] text-balance font-display text-2xl font-medium tracking-tight">
                {greenhouse.name} · {formatCropLabel(crop)}
              </h1>
              <span className="inline-flex items-center gap-2 rounded-full bg-ink-800 px-3 py-1 text-xs outline-1 -outline-offset-1 outline-white/[0.07]">
                <span className="size-1.5 rounded-full bg-brand" />
                <span className="font-medium text-paper">Recorded history</span>
                <span className="text-mist">
                  {checkpoints.length} daily checkpoints
                  {compartments.length > 0 ? ` · ${compartments.length} compartments` : ''}
                </span>
              </span>
            </div>
            <p className="mt-2 max-w-[80ch] text-xs text-mist">{greenhouse.description}</p>
          </div>
          <div className="max-w-[36ch] text-right text-[11px] text-mist">
            Recorded data cannot be changed: recommendations against this history would be shadow
            proposals, never executed actions.
          </div>
        </div>

        <div className="mt-5">
          <DayNavigator
            viewingDay={viewingIndex}
            currentDay={latestIndex}
            totalDays={latestIndex}
            onSelectDay={setManualViewingIndex}
            onReturnToCurrent={() => setManualViewingIndex(null)}
            caption={`Recorded timeline · ${latestIndex} days`}
            formatDay={formatDay}
            currentLabel="latest recorded state"
          />
        </div>

        {compartments.length > 0 && (
          <div className="mt-4">
            <div role="tablist" aria-label="Compartment" className="flex flex-wrap gap-2">
              {compartments.map((compartment) => {
                const selected = compartment.compartment_id === activeCompartmentId
                return (
                  <button
                    key={compartment.compartment_id}
                    type="button"
                    role="tab"
                    aria-selected={selected}
                    onClick={() => setSelectedCompartmentId(compartment.compartment_id)}
                    className={cn(
                      'rounded-full px-3 py-1 text-xs outline-1 -outline-offset-1 transition-colors',
                      selected
                        ? 'bg-brand/10 text-brand outline-brand/30'
                        : 'bg-ink-800 text-mist outline-white/[0.07] hover:text-paper',
                    )}
                  >
                    {compartment.name}
                  </button>
                )
              })}
            </div>
            {activeCompartment?.description && (
              <p className="mt-2 text-[11px] text-mist">{activeCompartment.description}</p>
            )}
          </div>
        )}

        {state === null ? (
          <p className="mt-4 text-sm text-mist">No recorded state at this checkpoint.</p>
        ) : (
          <>
            <p className="mt-4 text-xs text-mist" title={state.timestamp}>
              State as last observed at {formatCheckpoint(state.timestamp)} (
              {new Date(state.timestamp).toISOString().replace('.000Z', 'Z')})
            </p>
            {activeCompartmentId !== null && compartmentState === null && (
              <p className="mt-2 text-xs text-mist">
                Nothing recorded for this compartment yet at this checkpoint.
              </p>
            )}
            <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4">
              <Tile
                label="Air temperature"
                value={formatReading(environment.air_temperature_c, '°C')}
                hint={`heating setpoint ${formatReading(environment.heating_temperature_setpoint_c, '°C')} · ventilation ${formatReading(environment.ventilation_temperature_setpoint_c, '°C')}`}
              />
              <Tile
                label="Relative humidity"
                value={formatReading(environment.relative_humidity_pct, '%', 0)}
                hint={`deficit ${formatReading(environment.humidity_deficit_g_m3, 'g/m³')} · setpoint ${formatReading(environment.humidity_deficit_setpoint_g_m3, 'g/m³')}`}
              />
              <Tile
                label="CO₂"
                value={formatReading(environment.co2_ppm, 'ppm', 0)}
                hint={`setpoint ${formatReading(environment.co2_setpoint_ppm, 'ppm', 0)}`}
              />
              <Tile
                label="PAR"
                value={formatReading(environment.par_umol_m2_s, 'µmol/m²/s', 0)}
                hint={`lamps ${formatReading(environment.lamps_activation_pct, '%', 0)} · setpoint ${formatReading(environment.lamps_activation_setpoint_pct, '%', 0)}`}
              />
            </div>

            <div className="mt-4 grid gap-4 md:grid-cols-3">
              <ControlPanel
                title="Screens and windows"
                rows={[
                  ['Energy screen', formatReading(environment.energy_screen_position_pct, '%', 0)],
                  [
                    'Blackout screen',
                    formatReading(environment.blackout_screen_position_pct, '%', 0),
                  ],
                  ['Window, lee side', formatReading(environment.window_position_lee_pct, '%', 0)],
                  [
                    'Window, wind side',
                    formatReading(environment.window_position_wind_pct, '%', 0),
                  ],
                  ['Heating pipe', formatReading(environment.heating_pipe_temperature_c, '°C')],
                ]}
              />
              <ControlPanel
                title="Irrigation"
                rows={[
                  ['Flow duration', formatReading(environment.irrigation_flow_duration_min, 'min')],
                  [
                    'Interval setpoint',
                    formatReading(environment.irrigation_interval_setpoint_min, 'min', 0),
                  ],
                  ['Drain volume', formatReading(environment.drain_water_volume_l_m2, 'L/m²', 2)],
                  ['Drain EC', formatReading(environment.drain_ec_ds_m, 'dS/m', 2)],
                  ['Drain pH', formatReading(environment.drain_ph, '', 2)],
                ]}
              />
              <ControlPanel
                title="Crop samples"
                rows={[
                  [
                    'Fruit per sampled plant',
                    formatReading(environment.sampled_fruit_count_per_plant, ''),
                  ],
                  [
                    'Fresh weight per sampled plant',
                    formatReading(environment.sampled_fruit_fresh_weight_g_per_plant, 'g'),
                  ],
                  [
                    'Plant density',
                    formatReading(environment.plant_density_per_m2, 'plants/m²', 0),
                  ],
                  ['Harvested total', formatMass(harvestedG)],
                  ...(compartments.length > 0
                    ? ([['Whole greenhouse harvested', formatMass(state.total_harvested_g)]] as [
                        string,
                        string,
                      ][])
                    : []),
                ]}
              />
            </div>

            <div className="mt-4 grid gap-4 md:grid-cols-3">
              <ControlPanel
                title="Control: setpoint → effective (VIP)"
                rows={[
                  [
                    'Heating temperature',
                    `${formatReading(environment.heating_temperature_setpoint_c, '°C')} → ${formatReading(environment.heating_temperature_effective_c, '°C')}`,
                  ],
                  [
                    'Ventilation, lee side',
                    `${formatReading(environment.ventilation_temperature_setpoint_c, '°C')} → ${formatReading(environment.ventilation_temperature_lee_effective_c, '°C')}`,
                  ],
                  [
                    'CO₂',
                    `${formatReading(environment.co2_setpoint_ppm, 'ppm', 0)} → ${formatReading(environment.co2_effective_ppm, 'ppm', 0)}`,
                  ],
                  [
                    'Humidity deficit',
                    `${formatReading(environment.humidity_deficit_setpoint_g_m3, 'g/m³')} → ${formatReading(environment.humidity_deficit_effective_g_m3, 'g/m³')}`,
                  ],
                  [
                    'Irrigation interval',
                    `${formatReading(environment.irrigation_interval_setpoint_min, 'min', 0)} → ${formatReading(environment.irrigation_interval_effective_min, 'min', 0)}`,
                  ],
                  [
                    'Minimum pipe temperature',
                    `${formatReading(environment.minimum_pipe_temperature_setpoint_c, '°C')} → ${formatReading(environment.minimum_pipe_temperature_effective_c, '°C')}`,
                  ],
                  [
                    'CO₂ dosing',
                    environment.co2_dosing_on === null || environment.co2_dosing_on === undefined
                      ? '—'
                      : `${environment.co2_dosing_on >= 0.5 ? 'On' : 'Off'} · ${formatReading(environment.co2_dosing_minutes_since_reset, 'min', 0)} since reset`,
                  ],
                ]}
              />
              <ControlPanel
                title="Energy and costs today (per m²)"
                rows={[
                  [
                    'Heating energy',
                    formatReading(environment.heating_energy_today_mj_m2, 'MJ', 2),
                  ],
                  [
                    'Lighting electricity',
                    formatReading(environment.lighting_electricity_today_kwh_m2, 'kWh', 2),
                  ],
                  ['CO₂ dosed', formatReading(environment.co2_dosed_today_kg_m2, 'kg', 3)],
                  ['Costs (heating, lighting, CO₂, fixed)', costsToday],
                ]}
              />
              <ControlPanel
                title="Outside weather (site)"
                rows={[
                  [
                    'Air temperature',
                    formatReading(state.environment.outside_air_temperature_c, '°C'),
                  ],
                  [
                    'Relative humidity',
                    formatReading(state.environment.outside_relative_humidity_pct, '%', 0),
                  ],
                  [
                    'Global radiation',
                    formatReading(state.environment.outside_global_radiation_w_m2, 'W/m²', 0),
                  ],
                  [
                    'Radiation today (measured / forecast)',
                    `${formatReading(state.environment.outside_radiation_sum_j_cm2, '', 0)} / ${formatReading(state.environment.forecast_radiation_sum_today_j_cm2, '', 0)} J/cm²`,
                  ],
                  ['Wind speed', formatReading(state.environment.outside_wind_speed_m_s, 'm/s')],
                  [
                    'Rain',
                    state.environment.outside_rain === null ||
                    state.environment.outside_rain === undefined
                      ? '—'
                      : state.environment.outside_rain >= 0.5
                        ? 'Raining'
                        : 'Dry',
                  ],
                ]}
              />
            </div>
          </>
        )}
      </main>
    </AppShell>
  )
}
