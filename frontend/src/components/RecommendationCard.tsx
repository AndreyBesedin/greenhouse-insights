import { cn } from '../lib/utils'
import type { components } from '../../generated/schema'

type Recommendation = components['schemas']['Recommendation']
type RecommendationStatus = components['schemas']['RecommendationStatus']

const STATUS_META: Record<RecommendationStatus, { label: string; text: string; bg: string }> = {
  PENDING: { label: 'Pending', text: 'text-amber', bg: 'bg-amber/10' },
  EXECUTED: { label: 'Executed', text: 'text-brand', bg: 'bg-brand/10' },
  DISMISSED: { label: 'Dismissed', text: 'text-mist', bg: 'bg-ink-700' },
  REJECTED_BY_VALIDATOR: { label: 'Rejected', text: 'text-terra', bg: 'bg-terra/10' },
}

function actionMeta(action: Recommendation['action']) {
  switch (action.action_type) {
    case 'WATER_PLANT':
      return {
        label: 'Water',
        buttonLabel: `Water ${action.amount_ml} ml`,
        paramLine: `Recommended: ${action.amount_ml} ml`,
      }
    case 'HARVEST_PLANT':
      return { label: 'Harvest', buttonLabel: 'Harvest ripe fruit', paramLine: null }
    case 'LOWER_PLANT':
      return {
        label: 'Lower',
        buttonLabel: `Lower ${action.amount_cm} cm`,
        paramLine: `Recommended: ${action.amount_cm} cm`,
      }
    case 'SCHEDULE_INSPECTION':
      return { label: 'Inspect', buttonLabel: 'Schedule inspection', paramLine: null }
  }
}

interface RecommendationCardProps {
  recommendation: Recommendation
  interactive: boolean
  isBusy: boolean
  onApprove: () => void
  onDismiss: () => void
}

export function RecommendationCard({
  recommendation,
  interactive,
  isBusy,
  onApprove,
  onDismiss,
}: RecommendationCardProps) {
  const meta = actionMeta(recommendation.action)
  const isPending = recommendation.status === 'PENDING'
  const statusMeta = STATUS_META[recommendation.status]

  return (
    <div className="rounded-md bg-ink-800 p-3.5 outline-1 -outline-offset-1 outline-white/[0.05]">
      <div className="flex items-start justify-between gap-2">
        <div className="font-display text-sm font-medium">
          {recommendation.plant_id} · {meta.label}
        </div>
        {(!interactive || !isPending) && (
          <span
            className={cn(
              'shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium',
              statusMeta.bg,
              statusMeta.text,
            )}
          >
            {statusMeta.label}
          </span>
        )}
      </div>

      <p className="mt-1.5 text-xs text-mist">{recommendation.reason}</p>
      {meta.paramLine && <p className="mt-1 text-xs text-paper">{meta.paramLine}</p>}
      {recommendation.status === 'REJECTED_BY_VALIDATOR' && recommendation.rejection_reason && (
        <p className="mt-1 text-xs text-terra">{recommendation.rejection_reason}</p>
      )}

      {interactive && isPending && (
        <div className="mt-3 flex gap-2">
          <button
            type="button"
            onClick={onApprove}
            disabled={isBusy}
            className="rounded-md bg-brand px-2.5 py-1.5 text-xs font-medium text-ink transition-colors hover:bg-brand/90 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {meta.buttonLabel}
          </button>
          <button
            type="button"
            onClick={onDismiss}
            disabled={isBusy}
            className="rounded-md px-2.5 py-1.5 text-xs text-mist transition-colors hover:text-paper disabled:cursor-not-allowed disabled:opacity-40"
          >
            Dismiss
          </button>
        </div>
      )}
    </div>
  )
}
