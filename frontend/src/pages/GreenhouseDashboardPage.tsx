import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { apiClient } from '../api/client'
import { AppShell } from '../components/AppShell'
import { DayNavigator } from '../components/DayNavigator'
import { GreenhouseMap } from '../components/GreenhouseMap'
import { PlantDetailPanel } from '../components/PlantDetailPanel'
import { useGreenhouseState } from '../hooks/useGreenhouseState'
import { usePlantDetail } from '../hooks/usePlantDetail'
import { usePlantHistory } from '../hooks/usePlantHistory'
import { useSimulationStatus } from '../hooks/useSimulationStatus'
import { formatCropLabel, formatMass } from '../lib/format'
import { cn } from '../lib/utils'
import type { components } from '../../generated/schema'

type GreenhouseDetail = components['schemas']['GreenhouseDetail']
type SimulationSummary = components['schemas']['SimulationSummary']
type PlantHealth = components['schemas']['PlantState']['health']
type SimulationStatus = components['schemas']['SimulationStatus']
type ManagementPolicyType = components['schemas']['ManagementPolicyType']

const STATUS_META: Record<SimulationStatus, { label: string; dotCls: string }> = {
  NOT_STARTED: { label: 'Not started', dotCls: 'bg-amber' },
  RUNNING: { label: 'Running', dotCls: 'bg-brand' },
  COMPLETED: { label: 'Simulation completed', dotCls: 'bg-brand' },
  FAILED: { label: 'Failed', dotCls: 'bg-terra' },
}

const MANAGEMENT_POLICY_META: Record<ManagementPolicyType, string> = {
  NONE: 'Manual',
  DETERMINISTIC: 'Deterministic autopilot',
  AGENTIC: 'Agentic (scripted stand-in)',
}

function Kpi({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-lg bg-ink-850 p-4 outline-1 -outline-offset-1 outline-white/[0.06]">
      <div className="text-xs text-mist">{label}</div>
      <div className="mt-1.5 font-display text-2xl font-medium">{value}</div>
      {hint && <div className="mt-1 text-[11px] text-mist">{hint}</div>}
    </div>
  )
}

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

  if (detail === null) {
    return (
      <AppShell>
        <main className="mx-auto max-w-[1440px] px-6 py-10">
          <p className="text-sm text-mist">Loading greenhouse…</p>
        </main>
      </AppShell>
    )
  }

  if (detail.simulation === null) {
    return <NoDataSourceDashboard detail={detail} />
  }

  return <DashboardContent detail={detail} simulation={detail.simulation} />
}

function NoDataSourceDashboard({ detail }: { detail: GreenhouseDetail }) {
  const { greenhouse } = detail
  const crop = greenhouse.plants[0]?.variety ?? 'tomato'
  const [selectedPlantId, setSelectedPlantId] = useState<string | null>(null)
  const selectedPlant = greenhouse.plants.find((p) => p.plant_id === selectedPlantId) ?? null

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
            <h1 className="max-w-[28ch] text-balance font-display text-2xl font-medium tracking-tight">
              {greenhouse.name} · {formatCropLabel(crop)}
            </h1>
            <span className="mt-2 inline-flex items-center gap-2 rounded-full bg-ink-800 px-3 py-1 text-xs outline-1 -outline-offset-1 outline-white/[0.07]">
              <span className="size-1.5 rounded-full bg-mist" />
              <span className="font-medium text-paper">No data source connected</span>
            </span>
          </div>
          <div className="text-right text-xs text-mist">
            {greenhouse.plants.length.toLocaleString()} plants · {greenhouse.layout.rows} row
            {greenhouse.layout.rows > 1 ? 's' : ''}
          </div>
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_360px]">
          <section className="rounded-lg bg-ink-850 p-5 outline-1 -outline-offset-1 outline-white/[0.06]">
            <GreenhouseMap
              plants={greenhouse.plants}
              healthByPlantId={new Map()}
              selectedPlantId={selectedPlantId}
              onSelectPlant={setSelectedPlantId}
            />
          </section>

          <aside className="grid place-items-center rounded-lg bg-ink-850 p-10 text-center outline-1 -outline-offset-1 outline-white/[0.06]">
            <div>
              <div className="font-display text-sm font-medium text-paper">
                No data source connected yet
              </div>
              <p className="mt-1 text-xs text-mist">
                {selectedPlant
                  ? `Plant ${selectedPlant.plant_id} · Row ${selectedPlant.row}, position ${selectedPlant.position_in_row}. Connect live sensors or an external feed to see its state.`
                  : "This greenhouse doesn't have a simulation or live data source connected yet."}
              </p>
            </div>
          </aside>
        </div>
      </main>
    </AppShell>
  )
}

function DashboardContent({
  detail,
  simulation: initialSimulation,
}: {
  detail: GreenhouseDetail
  simulation: SimulationSummary
}) {
  const { greenhouse } = detail
  const { status, isAdvancing, nextDay } = useSimulationStatus(
    initialSimulation.simulation_id,
    initialSimulation,
  )
  const isFinished = status.status === 'COMPLETED' || status.status === 'FAILED'
  const statusMeta = STATUS_META[status.status]
  const crop = greenhouse.plants[0]?.variety ?? 'tomato'

  const [selectedPlantId, setSelectedPlantId] = useState<string | null>(null)
  const [manualViewingDay, setManualViewingDay] = useState<number | null>(null)
  const viewingDay = manualViewingDay ?? status.current_step

  async function handleNextDay() {
    await nextDay()
    // Advancing is an action on "today" - snap the view back to the new
    // current day even if the operator was browsing history.
    setManualViewingDay(null)
  }

  const state = useGreenhouseState(greenhouse.greenhouse_id, viewingDay)
  const plantDetail = usePlantDetail(greenhouse.greenhouse_id, selectedPlantId, viewingDay)
  const plantHistory = usePlantHistory(greenhouse.greenhouse_id, selectedPlantId, viewingDay)

  const healthByPlantId = new Map<string, PlantHealth>(
    (state?.plant_states ?? []).map((plantState) => [plantState.plant_id, plantState.health]),
  )

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
              <h1 className="max-w-[28ch] text-balance font-display text-2xl font-medium tracking-tight">
                {greenhouse.name} · {formatCropLabel(crop)}
              </h1>
              <span className="inline-flex items-center gap-2 rounded-full bg-ink-800 px-3 py-1 text-xs outline-1 -outline-offset-1 outline-white/[0.07]">
                <span className={cn('size-1.5 rounded-full', statusMeta.dotCls)} />
                <span className="font-medium text-paper">{statusMeta.label}</span>
                <span className="text-mist">
                  Day {status.current_step} / {status.total_steps}
                </span>
              </span>
              <span className="inline-flex items-center rounded-full bg-ink-800 px-3 py-1 text-xs text-mist outline-1 -outline-offset-1 outline-white/[0.07]">
                {MANAGEMENT_POLICY_META[status.management_policy]}
              </span>
            </div>
            <p className="mt-2 text-xs text-mist">
              {`${state?.plants_healthy ?? 0} healthy | ${state?.plants_monitor ?? 0} monitor | ` +
                `${state?.plants_action_required ?? 0} action required`}
            </p>
          </div>
          <div className="text-right text-xs text-mist">
            <div>
              {greenhouse.plants.length.toLocaleString()} plants · {greenhouse.layout.rows} row
              {greenhouse.layout.rows > 1 ? 's' : ''}
            </div>
            <button
              type="button"
              onClick={handleNextDay}
              disabled={isAdvancing || isFinished}
              className="mt-2 inline-flex items-center gap-2 rounded-md bg-brand px-3.5 py-2 text-sm font-medium text-ink transition-colors hover:bg-brand/90 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {isAdvancing ? 'Advancing…' : 'Next day →'}
            </button>
          </div>
        </div>

        <div className="mt-5">
          <DayNavigator
            viewingDay={viewingDay}
            currentDay={status.current_step}
            totalDays={status.total_steps}
            onSelectDay={setManualViewingDay}
            onReturnToCurrent={() => setManualViewingDay(null)}
          />
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-3">
          <Kpi
            label="Plants"
            value={greenhouse.plants.length.toLocaleString()}
            hint={`${greenhouse.layout.rows} row${greenhouse.layout.rows > 1 ? 's' : ''} · ${formatCropLabel(crop).toLowerCase()}`}
          />
          <Kpi label="Healthy" value={String(state?.plants_healthy ?? 0)} />
          <Kpi label="Monitor" value={String(state?.plants_monitor ?? 0)} />
          <Kpi label="Need action" value={String(state?.plants_action_required ?? 0)} />
          <Kpi
            label="Ready to harvest"
            value={formatMass(state?.total_ripe_mass_g ?? 0)}
            hint={(state?.total_ripe_mass_g ?? 0) > 0 ? 'ripe and waiting' : 'nothing ripe yet'}
          />
          <Kpi
            label="Harvested total"
            value={formatMass(state?.total_harvested_g ?? 0)}
            hint="cumulative this cycle"
          />
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_360px]">
          <section className="rounded-lg bg-ink-850 p-5 outline-1 -outline-offset-1 outline-white/[0.06]">
            <GreenhouseMap
              plants={greenhouse.plants}
              healthByPlantId={healthByPlantId}
              selectedPlantId={selectedPlantId}
              onSelectPlant={setSelectedPlantId}
            />
          </section>

          <PlantDetailPanel detail={plantDetail} history={plantHistory} />
        </div>
      </main>
    </AppShell>
  )
}
