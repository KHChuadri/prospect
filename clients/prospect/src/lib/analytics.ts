// Pure, client-side analytics derived from GET /api/applications data.
// Each JobApplication carries statusTransitions, so "ever reached a stage"
// can be computed without extra requests.
import type { ApplicationStatus, JobApplication } from './types'
import { APPLICATION_STATUSES } from './types'

// Linear pipeline order. Rejected/Withdrawn are off-ramps, not ranked here.
const PIPELINE: ApplicationStatus[] = ['Applied', 'Screening', 'Interviewing', 'Offer']

export const STATUS_COLORS: Record<ApplicationStatus, string> = {
  Applied: '#3b82f6', // blue-500
  Screening: '#eab308', // yellow-500
  Interviewing: '#f97316', // orange-500
  Offer: '#22c55e', // green-500
  Rejected: '#ef4444', // red-500
  Withdrawn: '#9ca3af', // gray-400
}

export function countByStatus(apps: JobApplication[]): Record<ApplicationStatus, number> {
  const counts = Object.fromEntries(
    APPLICATION_STATUSES.map((s) => [s, 0]),
  ) as Record<ApplicationStatus, number>
  for (const a of apps) counts[a.status]++
  return counts
}

// Every status an application has ever held (current + both ends of each transition).
function statusesEverHeld(app: JobApplication): Set<ApplicationStatus> {
  const set = new Set<ApplicationStatus>([app.status])
  for (const t of app.statusTransitions) {
    set.add(t.fromStatus)
    set.add(t.toStatus)
  }
  return set
}

function reachedStage(app: JobApplication, stage: ApplicationStatus): boolean {
  const target = PIPELINE.indexOf(stage)
  for (const s of statusesEverHeld(app)) {
    const i = PIPELINE.indexOf(s)
    if (i >= 0 && i >= target) return true
  }
  return false
}

const pct = (n: number, total: number) => (total === 0 ? 0 : Math.round((n / total) * 100))

export interface FunnelStats {
  total: number
  screened: number
  interviewing: number
  offers: number
  rejected: number
  responseRate: number
  interviewRate: number
  offerRate: number
}

export function funnelStats(apps: JobApplication[]): FunnelStats {
  const total = apps.length
  const screened = apps.filter((a) => reachedStage(a, 'Screening')).length
  const interviewing = apps.filter((a) => reachedStage(a, 'Interviewing')).length
  const offers = apps.filter((a) => reachedStage(a, 'Offer')).length
  const rejected = apps.filter((a) => a.status === 'Rejected').length
  return {
    total,
    screened,
    interviewing,
    offers,
    rejected,
    responseRate: pct(screened, total),
    interviewRate: pct(interviewing, total),
    offerRate: pct(offers, total),
  }
}

export function applicationsByMonth(apps: JobApplication[]): { month: string; count: number }[] {
  const map = new Map<string, number>()
  for (const a of apps) {
    const month = a.appliedAt.slice(0, 7) // 'YYYY-MM'
    map.set(month, (map.get(month) ?? 0) + 1)
  }
  return [...map.entries()]
    .map(([month, count]) => ({ month, count }))
    .sort((a, b) => a.month.localeCompare(b.month))
}
