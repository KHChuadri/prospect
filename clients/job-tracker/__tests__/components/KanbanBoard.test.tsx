import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { KanbanBoard } from '@/components/applications/KanbanBoard'
import type { JobApplication, ApplicationStatus } from '@/lib/types'

function app(id: number, company: string, status: ApplicationStatus): JobApplication {
  return {
    id, userId: 1, company, role: 'Engineer', status,
    source: null, salaryRange: null, appliedAt: '2024-01-01T00:00:00Z',
    notes: [], statusTransitions: [],
  }
}

function renderBoard(apps: JobApplication[]) {
  const client = new QueryClient()
  return render(
    <QueryClientProvider client={client}>
      <KanbanBoard applications={apps} />
    </QueryClientProvider>,
  )
}

describe('KanbanBoard', () => {
  it('renders a column for every status', () => {
    renderBoard([])
    ;(
      ['Applied', 'Screening', 'Interviewing', 'Offer', 'Rejected', 'Withdrawn'] as ApplicationStatus[]
    ).forEach((s) => {
      expect(screen.getByRole('region', { name: `${s} column` })).toBeInTheDocument()
    })
  })

  it('places each card in its status column', () => {
    renderBoard([app(1, 'Acme', 'Applied'), app(2, 'Globex', 'Offer')])
    const offerCol = screen.getByRole('region', { name: 'Offer column' })
    expect(offerCol).toHaveTextContent('Globex')
    const appliedCol = screen.getByRole('region', { name: 'Applied column' })
    expect(appliedCol).toHaveTextContent('Acme')
  })
})
