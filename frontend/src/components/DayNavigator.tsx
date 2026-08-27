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

  return (
    <nav>
      <button
        type="button"
        aria-label="Previous day"
        disabled={!isFinished || viewingDay <= 1}
        onClick={() => onSelectDay(viewingDay - 1)}
      >
        ← Previous day
      </button>
      <button
        type="button"
        aria-label="Next day"
        disabled={!isFinished || viewingDay >= totalDays}
        onClick={() => onSelectDay(viewingDay + 1)}
      >
        Next day →
      </button>
      <label>
        Day
        <input
          type="number"
          aria-label="Day"
          min={1}
          max={totalDays}
          value={viewingDay}
          disabled={!isFinished}
          onChange={(event) => {
            const day = Number(event.target.value)
            if (Number.isInteger(day) && day >= 1 && day <= totalDays) onSelectDay(day)
          }}
        />
      </label>
      {isViewingHistory && (
        <p>
          {`Viewing Day ${viewingDay}`}
          <br />
          {`Current state is Day ${currentDay}`}
          <br />
          <button type="button" onClick={onReturnToCurrent}>
            Return to Current Day
          </button>
        </p>
      )}
    </nav>
  )
}
