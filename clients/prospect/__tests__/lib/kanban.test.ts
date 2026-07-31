import { resolveDrop } from '@/lib/kanban'
import type { JobApplication, ApplicationStatus } from '@/lib/types'

function app(id: number, status: ApplicationStatus): JobApplication {
  return {
    id, userId: 1, company: 'Co', role: 'Eng', status,
    source: null, salaryRange: null, appliedAt: '2024-01-01T00:00:00Z',
    notes: [], statusTransitions: [],
  }
}

const apps = [app(1, 'Applied'), app(2, 'Interviewing')]

describe('resolveDrop', () => {
  it('moves to a column when dropped over a column id', () => {
    expect(resolveDrop(1, 'Offer', apps)).toEqual({ id: 1, newStatus: 'Offer' })
  })

  it('moves to the status of the card it was dropped over', () => {
    expect(resolveDrop(1, 2, apps)).toEqual({ id: 1, newStatus: 'Interviewing' })
  })

  it('returns null when dropped in its own column', () => {
    expect(resolveDrop(1, 'Applied', apps)).toBeNull()
  })

  it('returns null when over is null', () => {
    expect(resolveDrop(1, null, apps)).toBeNull()
  })

  it('returns null for an unknown active card', () => {
    expect(resolveDrop(99, 'Offer', apps)).toBeNull()
  })
})
