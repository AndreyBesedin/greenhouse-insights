import type { components } from '../../generated/schema'

type PlantDetail = components['schemas']['PlantDetail']

interface PlantDetailPanelProps {
  detail: PlantDetail | null
}

export function PlantDetailPanel({ detail }: PlantDetailPanelProps) {
  if (detail === null) {
    return <p>Select a plant to inspect its state.</p>
  }

  const { plant, state } = detail

  return (
    <section>
      <h2>{plant.plant_id}</h2>
      <p>{`Row ${plant.row} · Position ${plant.position_in_row}`}</p>
      {state === null ? (
        <p>No observations yet.</p>
      ) : (
        <dl>
          <dt>Health</dt>
          <dd>{state.health}</dd>
          {state.latest_soil_moisture_pct !== null &&
            state.latest_soil_moisture_pct !== undefined && (
              <>
                <dt>Soil moisture</dt>
                <dd>{`${state.latest_soil_moisture_pct}%`}</dd>
              </>
            )}
          {state.latest_visible_fruit_count !== null &&
            state.latest_visible_fruit_count !== undefined && (
              <>
                <dt>Visible fruit</dt>
                <dd>{state.latest_visible_fruit_count}</dd>
              </>
            )}
          {state.latest_ripe_fruit_count !== null &&
            state.latest_ripe_fruit_count !== undefined && (
              <>
                <dt>Ripe fruit</dt>
                <dd>{state.latest_ripe_fruit_count}</dd>
              </>
            )}
          {state.last_event_type && (
            <>
              <dt>Last event</dt>
              <dd>{state.last_event_type}</dd>
            </>
          )}
        </dl>
      )}
    </section>
  )
}
