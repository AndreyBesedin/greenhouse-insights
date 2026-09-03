import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { apiClient } from '../api/client'
import { AppShell } from '../components/AppShell'
import type { components } from '../../generated/schema'

type SourceType = components['schemas']['SourceType']
type ManagementPolicyType = components['schemas']['ManagementPolicyType']
type AgentProviderStatus = components['schemas']['AgentProviderStatus']

const SOURCE_TYPE_OPTIONS: { value: SourceType; label: string }[] = [
  { value: 'SIMULATION', label: 'Simulation' },
  { value: 'REAL_SENSORS', label: 'Real sensors' },
  { value: 'EXTERNAL_API', label: 'External API' },
  { value: 'IMPORTED_DATA', label: 'Imported data' },
]

const MANAGEMENT_POLICY_OPTIONS: { value: ManagementPolicyType; label: string }[] = [
  { value: 'NONE', label: 'None (manual only)' },
  { value: 'DETERMINISTIC', label: 'Deterministic (rule-based autopilot)' },
  { value: 'AGENTIC', label: 'Agentic' },
]

export function NewGreenhousePage() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [sourceType, setSourceType] = useState<SourceType>('SIMULATION')
  const [crop, setCrop] = useState('cherry_tomato')
  const [rows, setRows] = useState(4)
  const [columns, setColumns] = useState(10)
  const [durationDays, setDurationDays] = useState(28)
  const [randomSeed, setRandomSeed] = useState('')
  const [managementPolicy, setManagementPolicy] = useState<ManagementPolicyType>('DETERMINISTIC')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [agentProviderStatus, setAgentProviderStatus] = useState<AgentProviderStatus | null>(null)

  const isSimulation = sourceType === 'SIMULATION'

  useEffect(() => {
    let cancelled = false
    apiClient.GET('/system/agent-provider').then(({ data }) => {
      if (!cancelled) setAgentProviderStatus(data ?? null)
    })
    return () => {
      cancelled = true
    }
  }, [])

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)

    const { data, error: apiError } = await apiClient.POST('/greenhouses', {
      body: {
        name,
        description,
        source_type: sourceType,
        crop,
        rows,
        columns,
        duration_days: isSimulation ? durationDays : null,
        random_seed: isSimulation && randomSeed ? Number(randomSeed) : null,
        management_policy: isSimulation ? managementPolicy : null,
      },
    })

    setSubmitting(false)
    if (apiError || !data) {
      setError('Could not create the greenhouse. Check the fields and try again.')
      return
    }
    navigate(`/greenhouses/${data.greenhouse.greenhouse_id}`)
  }

  return (
    <AppShell>
      <main className="mx-auto max-w-[1440px] px-6 py-10">
        <div className="mb-6 text-xs text-mist">
          <Link to="/" className="transition-colors hover:text-paper">
            ← Greenhouses
          </Link>
        </div>

        <h1 className="mb-6 font-display text-xl font-medium tracking-tight">New greenhouse</h1>

        <form
          onSubmit={onSubmit}
          className="max-w-lg rounded-lg bg-ink-850 p-6 outline-1 -outline-offset-1 outline-white/[0.06]"
        >
          <label htmlFor="name" className="mb-1.5 block text-xs text-mist">
            Name
          </label>
          <input
            id="name"
            type="text"
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="mb-4 w-full rounded-md bg-ink-800 px-3.5 py-2.5 text-sm text-paper outline-1 -outline-offset-1 outline-white/[0.07] focus:outline-brand/50"
          />

          <label htmlFor="description" className="mb-1.5 block text-xs text-mist">
            Description
          </label>
          <input
            id="description"
            type="text"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            className="mb-4 w-full rounded-md bg-ink-800 px-3.5 py-2.5 text-sm text-paper outline-1 -outline-offset-1 outline-white/[0.07] focus:outline-brand/50"
          />

          <label htmlFor="source-type" className="mb-1.5 block text-xs text-mist">
            Data source
          </label>
          <select
            id="source-type"
            value={sourceType}
            onChange={(event) => setSourceType(event.target.value as SourceType)}
            className="mb-4 w-full rounded-md bg-ink-800 px-3.5 py-2.5 text-sm text-paper outline-1 -outline-offset-1 outline-white/[0.07] focus:outline-brand/50"
          >
            {SOURCE_TYPE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          {!isSimulation && (
            <p className="-mt-2 mb-4 text-[11px] text-mist">
              This data source isn't wired up to live ingestion yet — the greenhouse will be created
              without a running simulation.
            </p>
          )}

          <label htmlFor="crop" className="mb-1.5 block text-xs text-mist">
            Crop
          </label>
          <input
            id="crop"
            type="text"
            required
            value={crop}
            onChange={(event) => setCrop(event.target.value)}
            className="mb-4 w-full rounded-md bg-ink-800 px-3.5 py-2.5 text-sm text-paper outline-1 -outline-offset-1 outline-white/[0.07] focus:outline-brand/50"
          />

          <div className="mb-4 grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="rows" className="mb-1.5 block text-xs text-mist">
                Rows
              </label>
              <input
                id="rows"
                type="number"
                min={1}
                max={50}
                required
                value={rows}
                onChange={(event) => setRows(Number(event.target.value))}
                className="w-full rounded-md bg-ink-800 px-3.5 py-2.5 text-sm text-paper outline-1 -outline-offset-1 outline-white/[0.07] focus:outline-brand/50"
              />
            </div>
            <div>
              <label htmlFor="columns" className="mb-1.5 block text-xs text-mist">
                Columns
              </label>
              <input
                id="columns"
                type="number"
                min={1}
                max={50}
                required
                value={columns}
                onChange={(event) => setColumns(Number(event.target.value))}
                className="w-full rounded-md bg-ink-800 px-3.5 py-2.5 text-sm text-paper outline-1 -outline-offset-1 outline-white/[0.07] focus:outline-brand/50"
              />
            </div>
          </div>

          {isSimulation && (
            <div className="mb-4 grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="duration-days" className="mb-1.5 block text-xs text-mist">
                  Duration (days)
                </label>
                <input
                  id="duration-days"
                  type="number"
                  min={1}
                  max={200}
                  required={isSimulation}
                  value={durationDays}
                  onChange={(event) => setDurationDays(Number(event.target.value))}
                  className="w-full rounded-md bg-ink-800 px-3.5 py-2.5 text-sm text-paper outline-1 -outline-offset-1 outline-white/[0.07] focus:outline-brand/50"
                />
              </div>
              <div>
                <label htmlFor="random-seed" className="mb-1.5 block text-xs text-mist">
                  Random seed (optional)
                </label>
                <input
                  id="random-seed"
                  type="number"
                  value={randomSeed}
                  onChange={(event) => setRandomSeed(event.target.value)}
                  placeholder="auto"
                  className="w-full rounded-md bg-ink-800 px-3.5 py-2.5 text-sm text-paper outline-1 -outline-offset-1 outline-white/[0.07] placeholder:text-mist focus:outline-brand/50"
                />
              </div>
            </div>
          )}

          {isSimulation && (
            <div className="mb-4">
              <label htmlFor="management-policy" className="mb-1.5 block text-xs text-mist">
                Management policy
              </label>
              <select
                id="management-policy"
                value={managementPolicy}
                onChange={(event) =>
                  setManagementPolicy(event.target.value as ManagementPolicyType)
                }
                className="w-full rounded-md bg-ink-800 px-3.5 py-2.5 text-sm text-paper outline-1 -outline-offset-1 outline-white/[0.07] focus:outline-brand/50"
              >
                {MANAGEMENT_POLICY_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              {managementPolicy === 'AGENTIC' && agentProviderStatus?.status === 'CONFIGURED' && (
                <p className="mt-1.5 text-[11px] text-mist">
                  Agentic is configured to use a real model ({agentProviderStatus.model}) via the
                  Anthropic API — decisions are made by that model, and validated the same way as
                  any other policy before anything executes.
                </p>
              )}
              {managementPolicy === 'AGENTIC' && agentProviderStatus?.status === 'FAKE' && (
                <p className="mt-1.5 text-[11px] text-terra">
                  No real language model is configured — Agentic will run a scripted stand-in policy
                  instead of an actual model. The tool-calling and validation pipeline is real
                  either way. Please contact the application admin, or see the README (
                  GREENHOUSE_AGENT_PROVIDER / ANTHROPIC_API_KEY) to configure a real provider.
                </p>
              )}
              {managementPolicy === 'AGENTIC' &&
                agentProviderStatus?.status === 'MISCONFIGURED' && (
                  <p className="mt-1.5 text-[11px] text-terra">
                    {agentProviderStatus.detail
                      ? `Agentic is misconfigured: ${agentProviderStatus.detail} `
                      : 'Agentic is misconfigured. '}
                    Please contact the application admin, or see the README to fix this.
                  </p>
                )}
            </div>
          )}

          {error && <p className="mb-4 text-xs text-terra">{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="block w-full rounded-md bg-brand py-2.5 text-center text-sm font-medium text-ink transition-colors hover:bg-brand/90 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {submitting ? 'Creating…' : 'Create greenhouse'}
          </button>
        </form>
      </main>
    </AppShell>
  )
}
