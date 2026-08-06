import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '../mocks/server'
import EventsPage from '@/app/(app)/events/page'

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:5135/api'
const AGENT = process.env.NEXT_PUBLIC_AGENT_URL ?? 'http://localhost:8000'

// The assertion is on the request the page actually sends, so the handler
// records every /events URL rather than mocking the axios client.
function renderEventsPage() {
  const urls: URL[] = []
  server.use(
    http.get(`${AGENT}/events`, ({ request }) => {
      urls.push(new URL(request.url))
      return HttpResponse.json([])
    }),
    // A user who already has a city, so the timezone-seeding effect stays put.
    http.get(`${BASE}/users/me`, () =>
      HttpResponse.json({ email: 'a@test.local', city: 'Sydney' }),
    ),
    http.put(`${BASE}/users/me`, () =>
      HttpResponse.json({ email: 'a@test.local', city: 'Sydney' }),
    ),
  )
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  render(<QueryClientProvider client={qc}><EventsPage /></QueryClientProvider>)
  return urls
}

it('requests only_local=true by default', async () => {
  const urls = renderEventsPage()
  await waitFor(() => expect(urls.length).toBeGreaterThan(0))
  expect(urls[0].searchParams.get('only_local')).toBe('true')
  expect(urls[0].searchParams.get('saved')).toBe('false')
})

it('requests only_local=false after the toggle is switched off', async () => {
  const urls = renderEventsPage()
  await waitFor(() => expect(urls.length).toBeGreaterThan(0))

  await userEvent.click(await screen.findByRole('button', { name: /my city/i }))

  await waitFor(() =>
    expect(urls.some((u) => u.searchParams.get('only_local') === 'false')).toBe(true),
  )
})
