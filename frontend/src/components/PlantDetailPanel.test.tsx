import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { PlantDetailPanel } from './PlantDetailPanel'

const DETAIL = {
  plant: { plant_id: 'plant_017', variety: 'cherry_tomato', row: 2, position_in_row: 7 },
  state: {
    plant_id: 'plant_017',
    greenhouse_id: 'gh_001',
    simulated_day: 8,
    timestamp: '2026-01-09T00:00:00Z',
    health: 'HEALTHY',
    latest_soil_moisture_pct: 43,
    latest_visible_fruit_count: 47,
    latest_ripe_fruit_count: 12,
    last_event_type: 'WATERING',
    last_event_timestamp: '2026-01-08T10:00:00Z',
    provenance: 'DETERMINISTICALLY_DERIVED',
  },
} as const

describe('PlantDetailPanel', () => {
  it('prompts for a selection when no plant is chosen', () => {
    render(<PlantDetailPanel detail={null} history={null} />)

    expect(screen.getByText(/select a plant/i)).toBeInTheDocument()
  })

  it('shows plant position and health when state exists', () => {
    render(<PlantDetailPanel detail={DETAIL} history={null} />)

    expect(screen.getByText('plant_017')).toBeInTheDocument()
    expect(screen.getByText('Row 2 · Position 7')).toBeInTheDocument()
    expect(screen.getByText('Healthy')).toBeInTheDocument()
    expect(screen.getByText('43%')).toBeInTheDocument()
    expect(screen.getByText('47')).toBeInTheDocument()
    expect(screen.getByText('WATERING')).toBeInTheDocument()
  })

  it('shows a neutral message when the plant has no state yet', () => {
    render(
      <PlantDetailPanel
        detail={{
          plant: { plant_id: 'plant_017', variety: 'cherry_tomato', row: 2, position_in_row: 7 },
          state: null,
        }}
        history={null}
      />,
    )

    expect(screen.getByText(/no observations yet/i)).toBeInTheDocument()
  })

  it('shows the raw state as JSON on the Raw state tab', async () => {
    const user = userEvent.setup()
    render(<PlantDetailPanel detail={DETAIL} history={null} />)

    await user.click(screen.getByRole('button', { name: 'Raw state' }))

    expect(
      screen.getByText(
        (content, element) => element?.tagName === 'PRE' && content.includes('HEALTHY'),
      ),
    ).toBeInTheDocument()
  })

  it('shows history entries on the History tab', async () => {
    const user = userEvent.setup()
    render(
      <PlantDetailPanel
        detail={DETAIL}
        history={[
          {
            plant_id: 'plant_017',
            greenhouse_id: 'gh_001',
            simulated_day: 6,
            timestamp: '2026-01-07T00:00:00Z',
            health: 'MONITOR',
            latest_soil_moisture_pct: 30,
            latest_visible_fruit_count: 40,
            latest_ripe_fruit_count: 6,
            last_event_type: null,
            last_event_timestamp: null,
            provenance: 'DETERMINISTICALLY_DERIVED',
          } as const,
        ]}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'History' }))

    expect(screen.getByText('Day 6')).toBeInTheDocument()
  })
})
