import { CropIcon } from './CropIcon'
import { cropIconVariant } from '../lib/crop'
import type { PlantOperationalStatus } from '../lib/status'
import { STATUS_META } from '../lib/status'
import { cn } from '../lib/utils'

export function PlantMarker({
  plantId,
  row,
  positionInRow,
  crop,
  status,
  health,
  ripeFruitCount,
  ripeMassG,
  selected,
  onSelect,
}: {
  plantId: string
  row: number
  positionInRow: number
  crop: string
  status: PlantOperationalStatus
  /** Raw backend health value, exposed as a `data-health` attribute for tooling/tests. */
  health?: string
  ripeFruitCount?: number | null
  ripeMassG?: number | null
  selected: boolean
  onSelect: (plantId: string) => void
}) {
  const m = STATUS_META[status]
  const title = [
    `Plant ${plantId}`,
    m.label,
    ripeFruitCount != null ? `${ripeFruitCount} ripe` : null,
    ripeMassG != null ? `${ripeMassG} g ready` : null,
  ]
    .filter(Boolean)
    .join(' · ')

  return (
    <button
      type="button"
      onClick={() => onSelect(plantId)}
      aria-label={`Plant ${plantId}, row ${row} position ${positionInRow}, ${m.label}`}
      aria-pressed={selected}
      data-health={health}
      title={title}
      className={cn(
        'plant-fade relative grid place-items-center rounded-full outline-1 -outline-offset-1 transition-transform hover:scale-110 focus-visible:outline-2 focus-visible:outline-brand',
        m.bg,
        m.text,
        m.ring,
        selected ? 'size-8 outline-2 -outline-offset-2 outline-brand' : 'size-7',
      )}
    >
      {selected && (
        <span
          className="halo-pulse pointer-events-none absolute -inset-2 rounded-full bg-brand/25"
          aria-hidden
        />
      )}
      <CropIcon crop={cropIconVariant(crop)} size="sm" />
      {status === 'action-required' && (
        <span className="absolute -right-0.5 -top-0.5 size-2 rounded-full bg-terra" aria-hidden />
      )}
    </button>
  )
}
