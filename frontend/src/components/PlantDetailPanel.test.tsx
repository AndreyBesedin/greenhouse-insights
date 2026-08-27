import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { PlantDetailPanel } from './PlantDetailPanel'

describe('PlantDetailPanel', () => {
  it('prompts for a selection when no plant is chosen', () => {
    render(<PlantDetailPanel detail={null} />)

    expect(screen.getByText(/select a plant/i)).toBeInTheDocument()
  })

  it('shows plant position and health when state exists', () => {
    render(
      <PlantDetailPanel
        detail={{
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
        }}
      />,
    )

    expect(screen.getByText('plant_017')).toBeInTheDocument()
    expect(screen.getByText('Row 2 · Position 7')).toBeInTheDocument()
    expect(screen.getByText('HEALTHY')).toBeInTheDocument()
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
      />,
    )

    expect(screen.getByText(/no observations yet/i)).toBeInTheDocument()
  })
})
