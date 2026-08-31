import type { PlantOperationalStatus } from '../lib/status'
import { STATUS_META } from '../lib/status'
import { cn } from '../lib/utils'

export function StatusBadge({
  status,
  className,
}: {
  status: PlantOperationalStatus
  className?: string
}) {
  const m = STATUS_META[status]
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium outline-1 -outline-offset-1',
        m.bg,
        m.text,
        m.ring,
        className,
      )}
    >
      <span className={cn('size-1.5 rounded-full', m.dot)} aria-hidden />
      <span aria-hidden className="text-[10px] leading-none">
        {m.glyph}
      </span>
      {m.label}
    </span>
  )
}
