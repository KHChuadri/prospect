import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '../mocks/server'
import { ResumeMatchPanel } from '@/components/applications/ResumeMatchPanel'

const AGENT = process.env.NEXT_PUBLIC_AGENT_URL ?? 'http://localhost:8000'

function renderPanel() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(<QueryClientProvider client={qc}><ResumeMatchPanel appId={5} /></QueryClientProvider>)
}

test('analyze shows the score and gaps', async () => {
  renderPanel()
  await userEvent.click(screen.getByRole('button', { name: /analyze match/i }))
  await waitFor(() => expect(screen.getByText(/72/)).toBeInTheDocument())
  expect(screen.getByText('Docker')).toBeInTheDocument()      // missing
})

test('optimize shows the tailored résumé', async () => {
  renderPanel()
  await userEvent.click(screen.getByRole('button', { name: /optimize résumé/i }))
  await waitFor(() =>
    expect(screen.getByText('TAILORED RÉSUMÉ TEXT')).toBeInTheDocument(),
  )
})

test('match 409 shows the résumé prompt and no score', async () => {
  server.use(
    http.post(`${AGENT}/ai/match/:appId`, () =>
      HttpResponse.json({ detail: 'no résumé on file' }, { status: 409 }),
    ),
  )
  renderPanel()
  await userEvent.click(screen.getByRole('button', { name: /analyze match/i }))
  await waitFor(() => expect(screen.getByText(/upload your résumé/i)).toBeInTheDocument())
  expect(screen.queryByText(/fit score/i)).not.toBeInTheDocument()
})

test('match 409 for missing JD shows the JD prompt', async () => {
  server.use(
    http.post(`${AGENT}/ai/match/:appId`, () =>
      HttpResponse.json({ detail: 'no job description stored for this application' }, { status: 409 }),
    ),
  )
  renderPanel()
  await userEvent.click(screen.getByRole('button', { name: /analyze match/i }))
  await waitFor(() => expect(screen.getByText(/no job description stored/i)).toBeInTheDocument())
})
