import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '../api/client'
import type { components } from '../../generated/schema'
import { RecordedPlants } from './RecordedPlants'

vi.mock('../api/client', () => ({
  apiClient: { GET: vi.fn() },
}))

const mockedGet = vi.mocked(apiClient.GET)

type Plant = components['schemas']['Plant']
type PlantState = components['schemas']['PlantState']

function plant(plantId: string, row: number, position: number, zone: string): Plant {
  return {
    plant_id: plantId,
    variety: 'cherry',
    row,
    position_in_row: position,
    x: null,
    y: null,
    zone,
    tray_id: null,
  }
}

function state(
  plantId: string,
  timestamp: string,
  lastMeasuredAt: string | null,
  readings: Partial<PlantState> = {},
): PlantState {
  return {
    plant_id: plantId,
    greenhouse_id: 'wur_agc4_2023',
    compartment_id: 'pretrial',
    timestamp,
    health: 'UNKNOWN',
    last_measured_at: lastMeasuredAt,
    ...readings,
  } as PlantState
}

const PLANTS = [
  plant('wur23_p47b', 10, 2, 'med light / EC6'),
  plant('wur23_p42', 9, 2, 'high light / EC6'),
  plant('wur23_p41', 9, 1, 'high light / EC6'),
]
const CHECKPOINT = '2023-11-08T23:00:00Z'
const STATES = [
  state('wur23_p41', CHECKPOINT, '2023-11-01T11:00:00Z', {
    latest_plant_height_cm: 33,
    latest_leaf_count: 16,
    latest_truss_count: 10,
    latest_open_flower_count: 0,
    latest_green_fruit_count: 15,
    latest_coloured_fruit_count: 6,
    latest_ripe_fruit_count: 1,
  }),
  state('wur23_p42', CHECKPOINT, null),
]

beforeEach(() => {
  mockedGet.mockReset()
})

function renderPlants() {
  return render(
    <RecordedPlants
      greenhouseId="wur_agc4_2023"
      plants={PLANTS}
      states={STATES}
      upTo={CHECKPOINT}
    />,
  )
}

describe('RecordedPlants', () => {
  it('lists plants by field and repetition with their latest readings', () => {
    renderPlants()

    const table = screen.getByRole('table', { name: 'Measured plants' })
    const plantIds = within(table)
      .getAllByRole('button')
      .map((button) => button.textContent)
    expect(plantIds).toEqual(['wur23_p41', 'wur23_p42', 'wur23_p47b'])
    const measured = within(table).getByRole('button', { name: 'wur23_p41' }).closest('tr')
    expect(measured).not.toBeNull()
    expect(within(measured as HTMLElement).getByText('33.0 cm')).toBeInTheDocument()
    expect(within(measured as HTMLElement).getByText('1 Nov 2023')).toBeInTheDocument()
    const unmeasured = within(table).getByRole('button', { name: 'wur23_p42' }).closest('tr')
    expect(within(unmeasured as HTMLElement).getAllByText('—').length).toBeGreaterThan(1)
    expect(mockedGet).not.toHaveBeenCalled()
  })

  it('shows one history row per measurement up to the viewed checkpoint', async () => {
    mockedGet.mockResolvedValue({
      data: [
        state('wur23_p41', '2023-10-30T23:00:00Z', '2023-10-25T10:00:00Z', {
          latest_plant_height_cm: 31.5,
        }),
        state('wur23_p41', '2023-11-01T23:00:00Z', '2023-11-01T11:00:00Z', {
          latest_plant_height_cm: 33,
        }),
        // later snapshots repeat the 1 November reading
        state('wur23_p41', '2023-11-02T23:00:00Z', '2023-11-01T11:00:00Z', {
          latest_plant_height_cm: 33,
        }),
      ],
      error: undefined,
      response: new Response(),
    } as never)
    renderPlants()

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'wur23_p41' }))
    })

    expect(mockedGet).toHaveBeenCalledWith(
      '/greenhouses/{greenhouse_id}/plants/{plant_id}/history',
      {
        params: {
          path: { greenhouse_id: 'wur_agc4_2023', plant_id: 'wur23_p41' },
          query: { up_to: CHECKPOINT },
        },
      },
    )
    const history = await screen.findByRole('table', { name: 'Measurement history' })
    const rows = within(history).getAllByRole('row').slice(1)
    expect(rows.map((row) => within(row).getAllByRole('cell')[0].textContent)).toEqual([
      '25 Oct 2023',
      '1 Nov 2023',
    ])
    expect(within(history).getByText('31.5 cm')).toBeInTheDocument()
  })

  it('hides the history when the selected plant is clicked again', async () => {
    mockedGet.mockResolvedValue({ data: [], error: undefined, response: new Response() } as never)
    renderPlants()
    const button = screen.getByRole('button', { name: 'wur23_p42' })

    await act(async () => {
      fireEvent.click(button)
    })
    expect(await screen.findByText('No measurements up to this checkpoint.')).toBeInTheDocument()
    expect(button).toHaveAttribute('aria-pressed', 'true')

    await act(async () => {
      fireEvent.click(button)
    })
    expect(screen.queryByText('No measurements up to this checkpoint.')).not.toBeInTheDocument()
  })
})
