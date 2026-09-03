import type { components } from '../../generated/schema'

type PlantHealth = components['schemas']['PlantHealth']

// Mirrors backend/intelligence/state_reconstruction.py's
// _ACTION_REQUIRED_SOIL_MOISTURE_PCT / _MONITOR_SOIL_MOISTURE_PCT - health is
// derived purely from soil moisture today, so this is the whole rule.
const ACTION_REQUIRED_THRESHOLD_PCT = 20
const MONITOR_THRESHOLD_PCT = 40

export function explainHealth(
  health: PlantHealth,
  soilMoisturePct: number | null | undefined,
): string | null {
  if (soilMoisturePct == null) return null
  if (health === 'ACTION_REQUIRED') {
    return `Soil moisture ${soilMoisturePct}% is below the ${ACTION_REQUIRED_THRESHOLD_PCT}% action-required threshold.`
  }
  if (health === 'MONITOR') {
    return `Soil moisture ${soilMoisturePct}% is below the ${MONITOR_THRESHOLD_PCT}% monitor threshold.`
  }
  return null
}
