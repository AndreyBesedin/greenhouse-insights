import { useEffect, useState } from 'react'

import { apiClient } from '../api/client'
import type { components } from '../../generated/schema'

type TimelineSummary = components['schemas']['TimelineSummary']

const EMPTY: TimelineSummary = { checkpoints: [], current_timestamp: null }

// The instants a greenhouse can be viewed at - one per persisted state
// snapshot - independent of what produced them (a simulated day, a recorded
// replay checkpoint). Pass something that changes whenever a new checkpoint
// may exist (e.g. the simulation's current_step) as refreshKey.
export function useTimeline(greenhouseId: string, refreshKey: number | string): TimelineSummary {
  const [timeline, setTimeline] = useState<TimelineSummary>(EMPTY)

  useEffect(() => {
    let cancelled = false
    apiClient
      .GET('/greenhouses/{greenhouse_id}/timeline', {
        params: { path: { greenhouse_id: greenhouseId } },
      })
      .then(({ data }) => {
        if (!cancelled) setTimeline(data ?? EMPTY)
      })
    return () => {
      cancelled = true
    }
  }, [greenhouseId, refreshKey])

  return timeline
}
