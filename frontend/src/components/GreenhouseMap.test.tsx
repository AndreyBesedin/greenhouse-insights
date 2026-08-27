import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { GreenhouseMap } from './GreenhouseMap'
import type { components } from '../../generated/schema'

type PlantHealth = components['schemas']['PlantState']['health']

const PLANTS = [
  { plant_id: 'plant_001', variety: 'cherry_tomato', row: 1, position_in_row: 1 },
  { plant_id: 'plant_002', variety: 'cherry_tomato', row: 1, position_in_row: 2 },
]

function healthByPlantId(overrides: Record<string, PlantHealth> = {}) {
  return new Map(Object.entries(overrides))
}

describe('GreenhouseMap', () => {
  it('renders one clickable cell per plant', () => {
    render(
      <GreenhouseMap
        plants={PLANTS}
        healthByPlantId={healthByPlantId()}
        selectedPlantId={null}
        onSelectPlant={vi.fn()}
      />,
    )

    expect(screen.getByRole('button', { name: /plant_001/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /plant_002/ })).toBeInTheDocument()
  })

  it('reflects each plant health as a data attribute, defaulting to UNKNOWN', () => {
    render(
      <GreenhouseMap
        plants={PLANTS}
        healthByPlantId={healthByPlantId({ plant_001: 'ACTION_REQUIRED' })}
        selectedPlantId={null}
        onSelectPlant={vi.fn()}
      />,
    )

    expect(screen.getByRole('button', { name: /plant_001/ })).toHaveAttribute(
      'data-health',
      'ACTION_REQUIRED',
    )
    expect(screen.getByRole('button', { name: /plant_002/ })).toHaveAttribute(
      'data-health',
      'UNKNOWN',
    )
  })

  it('calls onSelectPlant with the plant id when a cell is clicked', () => {
    const onSelectPlant = vi.fn()
    render(
      <GreenhouseMap
        plants={PLANTS}
        healthByPlantId={healthByPlantId()}
        selectedPlantId={null}
        onSelectPlant={onSelectPlant}
      />,
    )

    screen.getByRole('button', { name: /plant_002/ }).click()

    expect(onSelectPlant).toHaveBeenCalledWith('plant_002')
  })

  it('marks the selected plant', () => {
    render(
      <GreenhouseMap
        plants={PLANTS}
        healthByPlantId={healthByPlantId()}
        selectedPlantId="plant_001"
        onSelectPlant={vi.fn()}
      />,
    )

    expect(screen.getByRole('button', { name: /plant_001/ })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(screen.getByRole('button', { name: /plant_002/ })).toHaveAttribute(
      'aria-pressed',
      'false',
    )
  })
})
