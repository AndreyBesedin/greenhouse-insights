import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { apiClient } from '../api/client'
import { AppShell } from '../components/AppShell'
import { CropIcon } from '../components/CropIcon'
import type { components } from '../../generated/schema'
import { cropIconVariant } from '../lib/crop'
import { formatCropLabel } from '../lib/format'
import { MANAGEMENT_POLICY_LABEL } from '../lib/managementPolicy'
import { cn } from '../lib/utils'

type GreenhouseListItem = components['schemas']['GreenhouseListItem']
type SimulationStatus = components['schemas']['SimulationStatus']

const STATUS_BADGE: Record<SimulationStatus, { label: string; cls: string }> = {
  NOT_STARTED: { label: 'Not started', cls: 'bg-amber/10 text-amber outline-amber/30' },
  RUNNING: { label: 'Running', cls: 'bg-brand/10 text-brand outline-brand/30' },
  COMPLETED: { label: 'Simulation completed', cls: 'bg-brand/10 text-brand outline-brand/30' },
  FAILED: { label: 'Failed', cls: 'bg-terra/10 text-terra outline-terra/30' },
}

const NO_SOURCE_BADGE = { label: 'No data source', cls: 'bg-ink-800 text-mist outline-white/15' }
const RECORDED_BADGE = { label: 'Recorded history', cls: 'bg-brand/10 text-brand outline-brand/30' }

function GreenhouseCard({
  greenhouse,
  isConfirmingDelete,
  isDeleting,
  onRequestDelete,
  onCancelDelete,
  onConfirmDelete,
}: {
  greenhouse: GreenhouseListItem
  isConfirmingDelete: boolean
  isDeleting: boolean
  onRequestDelete: () => void
  onCancelDelete: () => void
  onConfirmDelete: () => void
}) {
  const hasSimulation = greenhouse.status !== null
  const isRecorded = greenhouse.source_type === 'IMPORTED_DATA'
  const badge =
    greenhouse.status !== null
      ? STATUS_BADGE[greenhouse.status]
      : isRecorded
        ? RECORDED_BADGE
        : NO_SOURCE_BADGE
  const totalSteps = greenhouse.total_steps ?? 0
  const currentStep = greenhouse.current_step ?? 0
  const pct = totalSteps > 0 ? Math.round((currentStep / totalSteps) * 100) : 0

  return (
    <Link
      to={`/greenhouses/${greenhouse.greenhouse_id}`}
      className="block rounded-lg bg-ink-850 p-5 outline-1 -outline-offset-1 outline-white/[0.06] transition-colors hover:outline-brand/30"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="mt-0.5 grid size-9 place-items-center rounded-full bg-brand/10 text-brand outline-1 -outline-offset-1 outline-brand/30">
            <CropIcon crop={cropIconVariant(greenhouse.crop)} size="md" />
          </span>
          <div>
            <div className="flex items-center gap-2">
              <div className="font-display text-base font-medium">{greenhouse.name}</div>
              {greenhouse.management_policy === 'AGENTIC' && (
                <span className="rounded-full bg-brand/10 px-2 py-0.5 text-[10px] font-medium text-brand outline-1 -outline-offset-1 outline-brand/30">
                  Recommended demo
                </span>
              )}
            </div>
            <div className="text-xs text-mist">
              {formatCropLabel(greenhouse.crop)}
              {isRecorded ? '' : ` · ${greenhouse.plant_count.toLocaleString()} plants`}
              {hasSimulation ? ` · ${totalSteps} simulated days` : ''}
              {greenhouse.management_policy
                ? ` · ${MANAGEMENT_POLICY_LABEL[greenhouse.management_policy]}`
                : ''}
            </div>
          </div>
        </div>
        <span
          className={cn(
            'inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] outline-1 -outline-offset-1',
            badge.cls,
          )}
        >
          <span className="size-1.5 rounded-full bg-current" aria-hidden />
          {badge.label}
        </span>
      </div>

      {hasSimulation ? (
        <div className="mt-4">
          <div className="mb-1.5 flex justify-between text-[11px] text-mist">
            <span>
              Day {currentStep} of {totalSteps}
            </span>
            <span>{pct}%</span>
          </div>
          <div className="h-1 rounded-full bg-ink-600">
            <div
              className={cn(
                'h-full rounded-full',
                greenhouse.status === 'NOT_STARTED' ? 'bg-amber' : 'bg-brand',
              )}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      ) : isRecorded ? (
        <p className="mt-4 text-[11px] text-mist">
          Imported recorded history · browse it day by day.
        </p>
      ) : (
        <p className="mt-4 text-[11px] text-mist">Not yet connected to a live data source.</p>
      )}

      {isConfirmingDelete ? (
        <div className="mt-4 flex items-center justify-between gap-2">
          <span className="text-[11px] text-terra">Delete this greenhouse for good?</span>
          <div className="flex shrink-0 gap-2">
            <button
              type="button"
              disabled={isDeleting}
              onClick={(event) => {
                event.preventDefault()
                event.stopPropagation()
                onCancelDelete()
              }}
              className="rounded-md px-2 py-1 text-xs text-mist transition-colors hover:text-paper disabled:cursor-not-allowed disabled:opacity-40"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={isDeleting}
              onClick={(event) => {
                event.preventDefault()
                event.stopPropagation()
                onConfirmDelete()
              }}
              className="rounded-md bg-terra/10 px-2 py-1 text-xs font-medium text-terra outline-1 -outline-offset-1 outline-terra/40 transition-colors hover:bg-terra/20 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {isDeleting ? 'Deleting…' : 'Delete'}
            </button>
          </div>
        </div>
      ) : (
        <div className="mt-4 flex items-center justify-between">
          <span className="text-xs font-medium text-brand">Open greenhouse →</span>
          <button
            type="button"
            onClick={(event) => {
              event.preventDefault()
              event.stopPropagation()
              onRequestDelete()
            }}
            className="rounded-md px-2 py-1 text-[11px] text-mist transition-colors hover:text-terra"
          >
            Delete
          </button>
        </div>
      )}
    </Link>
  )
}

export function GreenhouseListPage() {
  const [greenhouses, setGreenhouses] = useState<GreenhouseListItem[] | null>(null)
  const [confirmingDeleteId, setConfirmingDeleteId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    apiClient.GET('/greenhouses').then(({ data }) => {
      if (!cancelled && data) setGreenhouses(data)
    })
    return () => {
      cancelled = true
    }
  }, [])

  async function handleConfirmDelete(greenhouseId: string) {
    setError(null)
    setDeletingId(greenhouseId)
    const { error: apiError } = await apiClient.DELETE('/greenhouses/{greenhouse_id}', {
      params: { path: { greenhouse_id: greenhouseId } },
    })
    setDeletingId(null)
    setConfirmingDeleteId(null)
    if (apiError) {
      setError('Could not delete that greenhouse. Try again.')
      return
    }
    setGreenhouses((current) => current?.filter((g) => g.greenhouse_id !== greenhouseId) ?? null)
  }

  return (
    <AppShell>
      <main className="mx-auto max-w-[1440px] px-6 py-10">
        <div className="mb-6 flex items-end justify-between">
          <div>
            <h1 className="max-w-[40ch] text-balance font-display text-xl font-medium tracking-tight">
              Greenhouses
            </h1>
            <p className="mt-1 text-sm text-mist">
              Monitor your growing environments and daily operations
              {greenhouses ? ` · ${greenhouses.length} greenhouses` : ''}
            </p>
          </div>
          <Link
            to="/greenhouses/new"
            className="inline-flex items-center gap-2 rounded-md bg-brand px-3.5 py-2 text-sm font-medium text-ink transition-colors hover:bg-brand/90"
          >
            New greenhouse
          </Link>
        </div>

        {error && <p className="mb-4 text-xs text-terra">{error}</p>}

        {greenhouses === null ? (
          <p className="text-sm text-mist">Loading greenhouses…</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-3">
            {greenhouses.map((greenhouse) => (
              <GreenhouseCard
                key={greenhouse.greenhouse_id}
                greenhouse={greenhouse}
                isConfirmingDelete={confirmingDeleteId === greenhouse.greenhouse_id}
                isDeleting={deletingId === greenhouse.greenhouse_id}
                onRequestDelete={() => setConfirmingDeleteId(greenhouse.greenhouse_id)}
                onCancelDelete={() => setConfirmingDeleteId(null)}
                onConfirmDelete={() => handleConfirmDelete(greenhouse.greenhouse_id)}
              />
            ))}
          </div>
        )}
      </main>
    </AppShell>
  )
}
