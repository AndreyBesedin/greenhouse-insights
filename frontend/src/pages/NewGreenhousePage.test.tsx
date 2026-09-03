import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '../api/client'
import { NewGreenhousePage } from './NewGreenhousePage'

vi.mock('../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn() },
}))

const mockedGet = vi.mocked(apiClient.GET)

function ok<T>(data: T) {
  return { data, error: undefined, response: new Response() }
}

beforeEach(() => {
  mockedGet.mockReset()
})

function renderPage() {
  return render(
    <MemoryRouter>
      <NewGreenhousePage />
    </MemoryRouter>,
  )
}

async function selectAgentic() {
  const user = userEvent.setup()
  await user.selectOptions(screen.getByLabelText('Management policy'), 'AGENTIC')
}

describe('NewGreenhousePage agent provider status', () => {
  it('shows a red warning when no real provider is configured', async () => {
    mockedGet.mockResolvedValue(ok({ status: 'FAKE', provider: 'fake', model: null, detail: null }))

    renderPage()
    await selectAgentic()

    const warning = await screen.findByText(/No real language model is configured/)
    expect(warning).toBeInTheDocument()
    expect(warning.className).toContain('text-terra')
  })

  it('shows a neutral note naming the model when a real provider is configured', async () => {
    mockedGet.mockResolvedValue(
      ok({ status: 'CONFIGURED', provider: 'anthropic', model: 'claude-sonnet-5', detail: null }),
    )

    renderPage()
    await selectAgentic()

    const note = await screen.findByText(/Agentic is configured to use a real model/)
    expect(note).toBeInTheDocument()
    expect(screen.getByText(/claude-sonnet-5/)).toBeInTheDocument()
    expect(note.className).not.toContain('text-terra')
  })

  it('shows a red warning with the detail when misconfigured', async () => {
    mockedGet.mockResolvedValue(
      ok({
        status: 'MISCONFIGURED',
        provider: 'anthropic',
        model: null,
        detail: 'GREENHOUSE_AGENT_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set.',
      }),
    )

    renderPage()
    await selectAgentic()

    const warning = await screen.findByText(/Agentic is misconfigured/)
    expect(warning).toBeInTheDocument()
    expect(warning.textContent).toContain('ANTHROPIC_API_KEY is not set')
    expect(warning.className).toContain('text-terra')
  })

  it('shows no agent provider note for the deterministic policy', async () => {
    mockedGet.mockResolvedValue(ok({ status: 'FAKE', provider: 'fake', model: null, detail: null }))

    renderPage()

    expect(await screen.findByLabelText('Management policy')).toBeInTheDocument()
    expect(screen.queryByText(/No real language model is configured/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Agentic is configured/)).not.toBeInTheDocument()
  })
})
