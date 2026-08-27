import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { DayNavigator } from './DayNavigator'

describe('DayNavigator', () => {
  it('is disabled while the simulation has not completed', () => {
    render(
      <DayNavigator
        viewingDay={3}
        currentDay={3}
        totalDays={28}
        isFinished={false}
        onSelectDay={vi.fn()}
        onReturnToCurrent={vi.fn()}
      />,
    )

    expect(screen.getByRole('button', { name: /previous day/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /next day/i })).toBeDisabled()
  })

  it('enables navigation once the simulation is finished', () => {
    render(
      <DayNavigator
        viewingDay={14}
        currentDay={28}
        totalDays={28}
        isFinished={true}
        onSelectDay={vi.fn()}
        onReturnToCurrent={vi.fn()}
      />,
    )

    expect(screen.getByRole('button', { name: /previous day/i })).toBeEnabled()
    expect(screen.getByRole('button', { name: /next day/i })).toBeEnabled()
  })

  it('calls onSelectDay with day-1/day+1 when prev/next are clicked', () => {
    const onSelectDay = vi.fn()
    render(
      <DayNavigator
        viewingDay={14}
        currentDay={28}
        totalDays={28}
        isFinished={true}
        onSelectDay={onSelectDay}
        onReturnToCurrent={vi.fn()}
      />,
    )

    screen.getByRole('button', { name: /previous day/i }).click()
    expect(onSelectDay).toHaveBeenCalledWith(13)

    screen.getByRole('button', { name: /next day/i }).click()
    expect(onSelectDay).toHaveBeenCalledWith(15)
  })

  it('disables next at the current day and previous at day 1', () => {
    const { rerender } = render(
      <DayNavigator
        viewingDay={28}
        currentDay={28}
        totalDays={28}
        isFinished={true}
        onSelectDay={vi.fn()}
        onReturnToCurrent={vi.fn()}
      />,
    )
    expect(screen.getByRole('button', { name: /next day/i })).toBeDisabled()

    rerender(
      <DayNavigator
        viewingDay={1}
        currentDay={28}
        totalDays={28}
        isFinished={true}
        onSelectDay={vi.fn()}
        onReturnToCurrent={vi.fn()}
      />,
    )
    expect(screen.getByRole('button', { name: /previous day/i })).toBeDisabled()
  })

  it('shows a return-to-current banner only when viewing a past day', () => {
    const { rerender } = render(
      <DayNavigator
        viewingDay={28}
        currentDay={28}
        totalDays={28}
        isFinished={true}
        onSelectDay={vi.fn()}
        onReturnToCurrent={vi.fn()}
      />,
    )
    expect(screen.queryByText(/return to current day/i)).not.toBeInTheDocument()

    rerender(
      <DayNavigator
        viewingDay={14}
        currentDay={28}
        totalDays={28}
        isFinished={true}
        onSelectDay={vi.fn()}
        onReturnToCurrent={vi.fn()}
      />,
    )
    expect(screen.getByText(/viewing day 14/i)).toBeInTheDocument()
    expect(screen.getByText(/current state is day 28/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /return to current day/i })).toBeInTheDocument()
  })

  it('the day input is disabled until finished and jumps to a typed day', () => {
    const onSelectDay = vi.fn()
    const { rerender } = render(
      <DayNavigator
        viewingDay={3}
        currentDay={3}
        totalDays={28}
        isFinished={false}
        onSelectDay={onSelectDay}
        onReturnToCurrent={vi.fn()}
      />,
    )
    expect(screen.getByLabelText('Day')).toBeDisabled()

    rerender(
      <DayNavigator
        viewingDay={3}
        currentDay={28}
        totalDays={28}
        isFinished={true}
        onSelectDay={onSelectDay}
        onReturnToCurrent={vi.fn()}
      />,
    )
    fireEvent.change(screen.getByLabelText('Day'), { target: { value: '17' } })

    expect(onSelectDay).toHaveBeenCalledWith(17)
  })
})
