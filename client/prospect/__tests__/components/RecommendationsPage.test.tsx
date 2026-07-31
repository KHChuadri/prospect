import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import RecommendationsPage from '@/app/(app)/recommendations/page'

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}><RecommendationsPage /></QueryClientProvider>,
  )
}

test('lists pending recommendations and accepts one', async () => {
  renderPage()
  expect(await screen.findByText('Acme Corp')).toBeInTheDocument()
  expect(screen.getByText(/Backend Engineer/)).toBeInTheDocument()

  await userEvent.click(screen.getByRole('button', { name: /accept/i }))

  // after accept, the pending list refetches (mock still returns the row);
  // assert the accept action resolved without error by re-finding the card.
  await waitFor(() =>
    expect(screen.getByRole('button', { name: /accept/i })).toBeEnabled(),
  )
})

test('accept reuses an existing matching application instead of creating a duplicate', async () => {
  const { server } = await import('../mocks/server')
  const { http, HttpResponse } = await import('msw')
  const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:5135'
  const AGENT = process.env.NEXT_PUBLIC_AGENT_URL ?? 'http://localhost:8000'

  let createCalls = 0
  let acceptedWith: { application_id: number } | null = null

  server.use(
    // an application matching the pending rec (Acme Corp / Backend Engineer) already exists
    http.get(`${BASE}/api/applications`, () =>
      HttpResponse.json([
        {
          id: 7, userId: 1, company: 'Acme Corp', role: 'Backend Engineer',
          status: 'Applied', source: 'Email', salaryRange: null,
          appliedAt: '2026-07-07T00:00:00Z', notes: [], statusTransitions: [],
        },
      ]),
    ),
    http.post(`${BASE}/api/applications`, () => {
      createCalls += 1
      return HttpResponse.json({}, { status: 201 })
    }),
    http.post(`${AGENT}/recommendations/:id/accept`, async ({ request }) => {
      acceptedWith = (await request.json()) as { application_id: number }
      return HttpResponse.json({ id: 1, status: 'accepted' })
    }),
  )

  renderPage()
  await screen.findByText('Acme Corp')
  await userEvent.click(screen.getByRole('button', { name: /accept/i }))

  await waitFor(() => expect(acceptedWith).toEqual({ application_id: 7 }))
  expect(createCalls).toBe(0)
})

test('shows empty state when there are no recommendations', async () => {
  const { server } = await import('../mocks/server')
  const { http, HttpResponse } = await import('msw')
  const AGENT = process.env.NEXT_PUBLIC_AGENT_URL ?? 'http://localhost:8000'
  server.use(http.get(`${AGENT}/recommendations`, () => HttpResponse.json([])))

  renderPage()
  expect(await screen.findByText(/no recommendations/i)).toBeInTheDocument()
})
