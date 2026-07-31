import {
  countByStatus,
  funnelStats,
  applicationsByMonth,
  STATUS_COLORS,
} from '@/lib/analytics'
import type { JobApplication, ApplicationStatus } from '@/lib/types'

function app(
  id: number,
  status: ApplicationStatus,
  appliedAt: string,
  reached: ApplicationStatus[] = [],
): JobApplication {
  return {
    id,
    userId: 1,
    company: `Co ${id}`,
    role: 'Engineer',
    status,
    source: null,
    salaryRange: null,
    appliedAt,
    notes: [],
    statusTransitions: reached.map((toStatus, i) => ({
      id: i,
      applicationId: id,
      fromStatus: 'Applied',
      toStatus,
      transitionedAt: appliedAt,
    })),
  }
}

describe('analytics', () => {
  const apps: JobApplication[] = [
    app(1, 'Applied', '2024-01-10T00:00:00Z'),
    app(2, 'Interviewing', '2024-01-20T00:00:00Z', ['Screening', 'Interviewing']),
    app(3, 'Offer', '2024-02-05T00:00:00Z', ['Screening', 'Interviewing', 'Offer']),
    app(4, 'Rejected', '2024-02-15T00:00:00Z', ['Screening', 'Interviewing']),
  ]

  it('countByStatus tallies every status, zero-filled', () => {
    const c = countByStatus(apps)
    expect(c.Applied).toBe(1)
    expect(c.Interviewing).toBe(1)
    expect(c.Offer).toBe(1)
    expect(c.Rejected).toBe(1)
    expect(c.Withdrawn).toBe(0)
  })

  it('funnelStats counts stages ever reached and computes rates', () => {
    const f = funnelStats(apps)
    expect(f.total).toBe(4)
    expect(f.screened).toBe(3) // apps 2,3,4 reached Screening
    expect(f.interviewing).toBe(3) // apps 2,3,4 reached Interviewing
    expect(f.offers).toBe(1) // app 3 reached Offer
    expect(f.rejected).toBe(1) // app 4 current status
    expect(f.interviewRate).toBe(75) // 3/4
    expect(f.offerRate).toBe(25) // 1/4
  })

  it('funnelStats is safe on empty input', () => {
    expect(funnelStats([])).toEqual({
      total: 0,
      screened: 0,
      interviewing: 0,
      offers: 0,
      rejected: 0,
      responseRate: 0,
      interviewRate: 0,
      offerRate: 0,
    })
  })

  it('applicationsByMonth groups and sorts ascending', () => {
    expect(applicationsByMonth(apps)).toEqual([
      { month: '2024-01', count: 2 },
      { month: '2024-02', count: 2 },
    ])
  })

  it('STATUS_COLORS has a hex for every status', () => {
    ;(
      ['Applied', 'Screening', 'Interviewing', 'Offer', 'Rejected', 'Withdrawn'] as ApplicationStatus[]
    ).forEach((s) => expect(STATUS_COLORS[s]).toMatch(/^#[0-9a-f]{6}$/i))
  })
})
