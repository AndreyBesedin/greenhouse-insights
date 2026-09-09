import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

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
    latest_estimated_ripe_mass_g: 300,
    harvested_total_g: 120,
    last_event_type: 'WATERING',
    last_event_timestamp: '2026-01-08T10:00:00Z',
    provenance: 'DETERMINISTICALLY_DERIVED',
  },
} as const

const ACTION_REQUIRED_DETAIL = {
  plant: DETAIL.plant,
  state: {
    ...DETAIL.state,
    health: 'ACTION_REQUIRED',
    latest_soil_moisture_pct: 18.5,
  },
} as const

function baseProps() {
  return {
    history: null,
    recommendations: null,
    interactive: true,
    isSubmittingAction: false,
    onSubmitAction: vi.fn(),
  }
}

describe('PlantDetailPanel', () => {
  it('prompts for a selection when no plant is chosen', () => {
    render(<PlantDetailPanel detail={null} {...baseProps()} />)

    expect(screen.getByText(/select a plant/i)).toBeInTheDocument()
  })

  it('shows plant position and health when state exists', () => {
    render(<PlantDetailPanel detail={DETAIL} {...baseProps()} />)

    expect(screen.getByText('plant_017')).toBeInTheDocument()
    expect(screen.getByText('Row 2 · Position 7')).toBeInTheDocument()
    expect(screen.getByText('Healthy')).toBeInTheDocument()
    expect(screen.getByText('43%')).toBeInTheDocument()
    expect(screen.getByText('47')).toBeInTheDocument()
    expect(screen.getByText('WATERING')).toBeInTheDocument()
  })

  it('labels sensor-derived metrics separately from ones that update immediately', () => {
    render(<PlantDetailPanel detail={DETAIL} {...baseProps()} />)

    expect(screen.getByText("Today's sensor reading")).toBeInTheDocument()
    expect(screen.getByText('Updates immediately')).toBeInTheDocument()
  })

  it('shows a neutral message when the plant has no state yet', () => {
    render(
      <PlantDetailPanel
        detail={{
          plant: { plant_id: 'plant_017', variety: 'cherry_tomato', row: 2, position_in_row: 7 },
          state: null,
        }}
        {...baseProps()}
      />,
    )

    expect(screen.getByText(/no observations yet/i)).toBeInTheDocument()
  })

  it('shows the raw state as JSON on the Raw state tab', async () => {
    const user = userEvent.setup()
    render(<PlantDetailPanel detail={DETAIL} {...baseProps()} />)

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
        {...baseProps()}
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
            latest_estimated_ripe_mass_g: 150,
            harvested_total_g: 0,
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

  it('does not show an attention banner for a healthy plant', () => {
    render(<PlantDetailPanel detail={DETAIL} {...baseProps()} />)

    expect(screen.queryByText(/below the/)).not.toBeInTheDocument()
    expect(screen.queryByText(/AI recommendation/)).not.toBeInTheDocument()
  })

  it('flags the missing recommendation for a non-healthy plant', () => {
    render(
      <PlantDetailPanel detail={ACTION_REQUIRED_DETAIL} {...baseProps()} recommendations={[]} />,
    )

    expect(screen.getByText(/No AI recommendation for this plant today/)).toBeInTheDocument()
  })

  it('says a recommendation already exists instead of the missing-recommendation note', () => {
    const recommendation = {
      recommendation_id: 'rec_1',
      source: { type: 'SIMULATION', source_id: 'sim_gh_001' },
      greenhouse_id: 'gh_001',
      simulated_day: 8,
      plant_id: 'plant_017',
      action: { action_type: 'WATER_PLANT', plant_id: 'plant_017', amount_ml: 700 },
      source_policy: 'DETERMINISTIC',
      status: 'PENDING',
      reason: 'Soil moisture low.',
      evidence: {},
      rejection_reason: null,
      approved_by: null,
      executed_by: null,
      requested_at: '2026-01-09T00:00:00Z',
      reviewed_at: null,
      executed_at: null,
    } as const

    render(
      <PlantDetailPanel
        detail={ACTION_REQUIRED_DETAIL}
        {...baseProps()}
        recommendations={[recommendation]}
      />,
    )

    expect(screen.getByText(/has a recommendation for this plant today/)).toBeInTheDocument()
    expect(screen.queryByText(/No AI recommendation/)).not.toBeInTheDocument()
  })

  it('hides quick actions when viewing a historical day', () => {
    render(<PlantDetailPanel detail={DETAIL} {...baseProps()} interactive={false} />)

    expect(screen.queryByRole('button', { name: /Water 700 ml/ })).not.toBeInTheDocument()
  })

  it('submits a manual water action with the default amount', async () => {
    const user = userEvent.setup()
    const onSubmitAction = vi.fn()
    render(<PlantDetailPanel detail={DETAIL} {...baseProps()} onSubmitAction={onSubmitAction} />)

    await user.click(screen.getByRole('button', { name: 'Water 700 ml' }))

    expect(onSubmitAction).toHaveBeenCalledWith({
      action_type: 'WATER_PLANT',
      plant_id: 'plant_017',
      amount_ml: 700,
    })
  })

  it('submits a manual harvest action', async () => {
    const user = userEvent.setup()
    const onSubmitAction = vi.fn()
    render(<PlantDetailPanel detail={DETAIL} {...baseProps()} onSubmitAction={onSubmitAction} />)

    await user.click(screen.getByRole('button', { name: 'Harvest ripe fruit' }))

    expect(onSubmitAction).toHaveBeenCalledWith({
      action_type: 'HARVEST_PLANT',
      plant_id: 'plant_017',
    })
  })

  it('disables quick action buttons while a submission is in flight', () => {
    render(<PlantDetailPanel detail={DETAIL} {...baseProps()} isSubmittingAction={true} />)

    expect(screen.getByRole('button', { name: 'Water 700 ml' })).toBeDisabled()
  })
})
