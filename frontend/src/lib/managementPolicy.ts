import type { components } from '../../generated/schema'

type ManagementPolicyType = components['schemas']['ManagementPolicyType']

export const MANAGEMENT_POLICY_LABEL: Record<ManagementPolicyType, string> = {
  NONE: 'Manual',
  DETERMINISTIC: 'Deterministic autopilot',
  AGENTIC: 'Agentic (scripted stand-in)',
}
