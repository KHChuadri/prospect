import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import ResumePage from '@/app/(app)/resume/page'
import { server } from '../mocks/server'

const AGENT = process.env.NEXT_PUBLIC_AGENT_URL ?? 'http://localhost:8000'

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(<QueryClientProvider client={qc}><ResumePage /></QueryClientProvider>)
}

test('loads the stored résumé and saves edits', async () => {
  renderPage()
  const box = await screen.findByRole('textbox')
  await waitFor(() => expect(box).toHaveValue('my stored résumé'))

  await userEvent.clear(box)
  await userEvent.type(box, 'updated résumé')
  await userEvent.click(screen.getByRole('button', { name: /save/i }))

  await waitFor(() => expect(screen.getByText(/saved/i)).toBeInTheDocument())
})

function pdfFile(name = 'cv.pdf', size = 1024) {
  const file = new File(['%PDF-1.4'], name, { type: 'application/pdf' })
  Object.defineProperty(file, 'size', { value: size })
  return file
}

test('uploading a PDF fills the editor and shows the parsed profile', async () => {
  renderPage()
  const input = await screen.findByLabelText(/upload a pdf/i)

  await userEvent.upload(input, pdfFile())

  const box = await screen.findByRole('textbox')
  await waitFor(() => expect(box).toHaveValue('JANE CHEN\nSenior Engineer'))
  expect(await screen.findByText('Jane Chen')).toBeInTheDocument()
  expect(screen.getByText('Python')).toBeInTheDocument()
  expect(screen.getByText(/Acme Corp/)).toBeInTheDocument()
})

test('rejects a non-PDF without calling the API', async () => {
  // The input carries accept="application/pdf", and userEvent honours it by
  // dropping non-matching files before they ever reach onChange. Opting out is
  // what lets us reach the runtime guard — which is not redundant with the
  // attribute: drag-and-drop and a renamed file both walk straight past accept.
  const user = userEvent.setup({ applyAccept: false })
  renderPage()
  const input = await screen.findByLabelText(/upload a pdf/i)

  await user.upload(input, new File(['hi'], 'cv.txt', { type: 'text/plain' }))

  expect(await screen.findByText(/only pdf files/i)).toBeInTheDocument()
})

test('rejects a file over 5 MB without calling the API', async () => {
  renderPage()
  const input = await screen.findByLabelText(/upload a pdf/i)

  await userEvent.upload(input, pdfFile('big.pdf', 6 * 1024 * 1024))

  expect(await screen.findByText(/5 MB/i)).toBeInTheDocument()
})

test('surfaces a server-side parse failure', async () => {
  server.use(
    http.post(`${AGENT}/ai/resume/ingest`, () =>
      HttpResponse.json({ detail: 'this PDF is password-protected' }, { status: 422 }),
    ),
  )
  renderPage()
  const input = await screen.findByLabelText(/upload a pdf/i)

  await userEvent.upload(input, pdfFile())

  expect(await screen.findByText(/password-protected/i)).toBeInTheDocument()
})
