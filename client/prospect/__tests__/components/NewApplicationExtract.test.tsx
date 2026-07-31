import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '../mocks/server'
import NewApplicationPage from '@/app/(app)/applications/new/page'

const AGENT = process.env.NEXT_PUBLIC_AGENT_URL ?? 'http://localhost:8000'

const push = jest.fn()
jest.mock('next/navigation', () => ({ useRouter: () => ({ push }) }))

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(<QueryClientProvider client={qc}><NewApplicationPage /></QueryClientProvider>)
}

beforeEach(() => {
  push.mockClear()
})

test('pasting a JD and extracting fills the company and role fields', async () => {
  renderPage()
  const jdBox = screen.getByPlaceholderText(/paste the job description/i)
  await userEvent.type(jdBox, 'Acme is hiring a Backend Engineer')
  await userEvent.click(screen.getByRole('button', { name: /extract/i }))

  await waitFor(() =>
    expect(screen.getByLabelText(/company/i)).toHaveValue('Acme Corp'),
  )
  expect(screen.getByLabelText(/role/i)).toHaveValue('Backend Engineer')
  // salary maps onto the salary range field
  expect(screen.getByLabelText(/salary/i)).toHaveValue('120k-150k')
})

test('navigates away even when storing the JD fails', async () => {
  server.use(
    http.put(`${AGENT}/ai/apps/:appId/jd`, () => HttpResponse.json({ detail: 'boom' }, { status: 500 })),
  )
  renderPage()
  const jdBox = screen.getByPlaceholderText(/paste the job description/i)
  await userEvent.type(jdBox, 'Acme is hiring a Backend Engineer')
  await userEvent.click(screen.getByRole('button', { name: /extract/i }))

  await waitFor(() =>
    expect(screen.getByLabelText(/company/i)).toHaveValue('Acme Corp'),
  )

  await userEvent.click(screen.getByRole('button', { name: /add application/i }))

  await waitFor(() => expect(push).toHaveBeenCalledWith('/'))
})
