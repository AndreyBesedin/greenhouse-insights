import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from './api/client'
import App from './App'

vi.mock('./api/client', () => ({
  apiClient: { GET: vi.fn() },
}))

beforeEach(() => {
  vi.mocked(apiClient.GET).mockReset()
})

describe('App', () => {
  it('renders the greenhouse list at the root route', async () => {
    vi.mocked(apiClient.GET).mockResolvedValue({
      data: [],
      error: undefined,
      response: new Response(),
    })

    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>,
    )

    expect(await screen.findByRole('heading', { name: /greenhouses/i })).toBeInTheDocument()
  })
})
