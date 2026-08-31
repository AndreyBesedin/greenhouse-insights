interface DayNavigatorProps {
  viewingDay: number
  currentDay: number
  totalDays: number
  isFinished: boolean
  onSelectDay: (day: number) => void
  onReturnToCurrent: () => void
}

export function DayNavigator({
  viewingDay,
  currentDay,
  totalDays,
  isFinished,
  onSelectDay,
  onReturnToCurrent,
}: DayNavigatorProps) {
  const isViewingHistory = viewingDay !== currentDay
  const pct = totalDays > 0 ? Math.round((viewingDay / totalDays) * 100) : 0

  return (
    <nav className="rounded-lg bg-ink-850 px-5 py-3.5 outline-1 -outline-offset-1 outline-white/[0.06]">
      <div className="mb-2.5 flex items-center justify-between text-xs">
        <span className="text-mist">Simulation timeline · {totalDays}-day cycle</span>
        <span className="font-medium text-paper">
          Day {viewingDay} of {totalDays}
        </span>
      </div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          aria-label="Previous day"
          disabled={!isFinished || viewingDay <= 1}
          onClick={() => onSelectDay(viewingDay - 1)}
          className="shrink-0 rounded-md px-2 py-1 text-xs text-mist transition-colors hover:text-paper disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:text-mist"
        >
          ← Previous day
        </button>

        <div className="relative h-1 flex-1 rounded-full bg-ink-600">
          <div
            className="absolute inset-y-0 left-0 rounded-full bg-brand/70"
            style={{ width: `${pct}%` }}
          />
          <input
            type="range"
            aria-label="Day"
            min={1}
            max={totalDays}
            value={viewingDay}
            disabled={!isFinished}
            onChange={(event) => {
              const day = Number(event.target.value)
              if (Number.isInteger(day) && day >= 1 && day <= totalDays) onSelectDay(day)
            }}
            className="absolute inset-0 h-full w-full cursor-pointer appearance-none bg-transparent accent-brand disabled:cursor-not-allowed [&::-webkit-slider-thumb]:size-3 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-brand"
          />
        </div>

        <button
          type="button"
          aria-label="Next day"
          disabled={!isFinished || viewingDay >= totalDays}
          onClick={() => onSelectDay(viewingDay + 1)}
          className="shrink-0 rounded-md px-2 py-1 text-xs text-mist transition-colors hover:text-paper disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:text-mist"
        >
          Next day →
        </button>
      </div>

      {isViewingHistory && (
        <div className="mt-3 flex items-center justify-between rounded-md bg-brand/[0.08] px-4 py-2.5 outline-1 -outline-offset-1 outline-brand/25">
          <span className="text-xs text-paper">
            Viewing Day {viewingDay} — current state is Day {currentDay}
          </span>
          <button
            type="button"
            onClick={onReturnToCurrent}
            className="cursor-pointer text-xs font-medium text-brand hover:underline"
          >
            Return to Current Day
          </button>
        </div>
      )}
    </nav>
  )
}
