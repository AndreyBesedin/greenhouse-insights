import { useId, useState } from 'react'

import { RecommendationCard } from './RecommendationCard'
import type { components } from '../../generated/schema'

type Recommendation = components['schemas']['Recommendation']

interface ManagementPanelProps {
  recommendations: Recommendation[] | null
  /** True only when viewing the current day - historical days show the
   * same recommendations read-only, never allowing a past decision to be
   * changed. */
  interactive: boolean
  busyId: string | null
  onApprove: (recommendationId: string) => void
  onDismiss: (recommendationId: string) => void
  isApprovingAll: boolean
  onApproveAll: () => void
}

export function ManagementPanel({
  recommendations,
  interactive,
  busyId,
  onApprove,
  onDismiss,
  isApprovingAll,
  onApproveAll,
}: ManagementPanelProps) {
  const [isOpen, setIsOpen] = useState(true)
  const bodyId = useId()

  return (
    <section className="rounded-lg bg-ink-850 p-5 outline-1 -outline-offset-1 outline-white/[0.06]">
      <button
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        aria-expanded={isOpen}
        aria-controls={bodyId}
        className="flex w-full items-center justify-between gap-3 text-left"
      >
        <span className="flex items-center gap-2">
          <ChevronIcon isOpen={isOpen} />
          <h2 className="font-display text-sm font-medium">AI assistant</h2>
        </span>
        {recommendations && recommendations.length > 0 && (
          <Summary recommendations={recommendations} />
        )}
      </button>

      {isOpen && (
        <div id={bodyId}>
          {recommendations === null && (
            <p className="mt-3 text-xs text-mist">Loading recommendations…</p>
          )}
          {recommendations !== null && recommendations.length === 0 && (
            <p className="mt-3 text-xs text-mist">No recommendations for this day.</p>
          )}
          {recommendations !== null && recommendations.length > 0 && (
            <RecommendationLists
              recommendations={recommendations}
              interactive={interactive}
              busyId={busyId}
              onApprove={onApprove}
              onDismiss={onDismiss}
              isApprovingAll={isApprovingAll}
              onApproveAll={onApproveAll}
            />
          )}
        </div>
      )}
    </section>
  )
}

function ChevronIcon({ isOpen }: { isOpen: boolean }) {
  return (
    <svg
      width={14}
      height={14}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={`shrink-0 text-mist transition-transform ${isOpen ? 'rotate-90' : ''}`}
      aria-hidden="true"
    >
      <path d="M9 6l6 6-6 6" />
    </svg>
  )
}

function Summary({ recommendations }: { recommendations: Recommendation[] }) {
  const executed = recommendations.filter((r) => r.status === 'EXECUTED').length
  const dismissed = recommendations.filter(
    (r) => r.status === 'DISMISSED' || r.status === 'REJECTED_BY_VALIDATOR',
  ).length
  return (
    <span className="text-[11px] text-mist">
      {recommendations.length} recommendation{recommendations.length === 1 ? '' : 's'}
      {executed > 0 && ` · ${executed} executed`}
      {dismissed > 0 && ` · ${dismissed} dismissed`}
    </span>
  )
}

function RecommendationLists({
  recommendations,
  interactive,
  busyId,
  onApprove,
  onDismiss,
  isApprovingAll,
  onApproveAll,
}: Omit<ManagementPanelProps, 'recommendations'> & { recommendations: Recommendation[] }) {
  const pending = recommendations.filter((r) => r.status === 'PENDING')
  const resolved = recommendations.filter((r) => r.status !== 'PENDING')

  return (
    <>
      {pending.length > 0 && (
        <div className="mt-3 space-y-2">
          {interactive && pending.length > 1 && (
            <div className="flex justify-end">
              <button
                type="button"
                disabled={isApprovingAll}
                onClick={onApproveAll}
                className="rounded-md bg-brand px-2.5 py-1.5 text-xs font-medium text-ink transition-colors hover:bg-brand/90 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {isApprovingAll ? 'Approving all…' : `Approve all (${pending.length})`}
              </button>
            </div>
          )}
          {pending.map((recommendation) => (
            <RecommendationCard
              key={recommendation.recommendation_id}
              recommendation={recommendation}
              interactive={interactive}
              isBusy={busyId === recommendation.recommendation_id}
              onApprove={() => onApprove(recommendation.recommendation_id)}
              onDismiss={() => onDismiss(recommendation.recommendation_id)}
            />
          ))}
        </div>
      )}
      {resolved.length > 0 && (
        <div className="mt-4">
          <h3 className="text-[11px] font-medium text-mist">
            {interactive ? 'Today’s actions' : 'That day’s actions'}
          </h3>
          <div className="mt-2 space-y-2">
            {resolved.map((recommendation) => (
              <RecommendationCard
                key={recommendation.recommendation_id}
                recommendation={recommendation}
                interactive={false}
                isBusy={false}
                onApprove={() => {}}
                onDismiss={() => {}}
              />
            ))}
          </div>
        </div>
      )}
    </>
  )
}
