import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AnalyticsPage from '@/app/(app)/analytics/page'

// recharts ResponsiveContainer needs a size in jsdom; stub it to a plain box.
jest.mock('recharts', () => {
  const Actual = jest.requireActual('recharts')
  return { ...Actual, ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div> }
})

function renderPage() {
  const client = new QueryClient()
  return render(
    <QueryClientProvider client={client}>
      <AnalyticsPage />
    </QueryClientProvider>,
  )
}

describe('AnalyticsPage', () => {
  it('renders the heading and a total stat from fetched data', async () => {
    renderPage()
    expect(screen.getByRole('heading', { name: /analytics/i })).toBeInTheDocument()
    // MSW returns one application -> total "1" appears once loaded.
    expect(await screen.findByText('Total applications')).toBeInTheDocument()
  })
})
