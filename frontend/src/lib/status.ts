import type { components } from '../../generated/schema'

type PlantHealth = components['schemas']['PlantHealth']

export type PlantOperationalStatus = 'healthy' | 'monitor' | 'action-required' | 'unknown'

const HEALTH_TO_STATUS: Record<PlantHealth, PlantOperationalStatus> = {
  HEALTHY: 'healthy',
  MONITOR: 'monitor',
  ACTION_REQUIRED: 'action-required',
  UNKNOWN: 'unknown',
}

export function healthToStatus(health: PlantHealth | null | undefined): PlantOperationalStatus {
  return health ? HEALTH_TO_STATUS[health] : 'unknown'
}

export const STATUS_META: Record<
  PlantOperationalStatus,
  { label: string; dot: string; text: string; ring: string; bg: string; glyph: string }
> = {
  healthy: {
    label: 'Healthy',
    dot: 'bg-brand',
    text: 'text-brand',
    ring: 'outline-brand/40',
    bg: 'bg-brand/10',
    glyph: '✓',
  },
  monitor: {
    label: 'Monitor',
    dot: 'bg-amber',
    text: 'text-amber',
    ring: 'outline-amber/40',
    bg: 'bg-amber/10',
    glyph: '!',
  },
  'action-required': {
    label: 'Action required',
    dot: 'bg-terra',
    text: 'text-terra',
    ring: 'outline-terra/50',
    bg: 'bg-terra/10',
    glyph: '▲',
  },
  unknown: {
    label: 'Unknown',
    dot: 'bg-mist',
    text: 'text-mist',
    ring: 'outline-white/15',
    bg: 'bg-ink-800',
    glyph: '?',
  },
}
