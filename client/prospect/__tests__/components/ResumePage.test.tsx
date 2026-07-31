import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ResumePage from '@/app/(app)/resume/page'

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
