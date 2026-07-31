import { Badge } from '@/components/ui/badge'
import type { ApplicationStatus } from '@/lib/types'

const STATUS_STYLES: Record<ApplicationStatus, string> = {
  Applied:      'bg-blue-500/15 text-blue-300 ring-1 ring-blue-500/30',
  Screening:    'bg-yellow-500/15 text-yellow-300 ring-1 ring-yellow-500/30',
  Interviewing: 'bg-orange-500/15 text-orange-300 ring-1 ring-orange-500/30',
  Offer:        'bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/30',
  Rejected:     'bg-red-500/15 text-red-300 ring-1 ring-red-500/30',
  Withdrawn:    'bg-zinc-500/15 text-zinc-300 ring-1 ring-zinc-500/30',
}

export function StatusBadge({ status }: { status: ApplicationStatus }) {
  return (
    <Badge className={STATUS_STYLES[status]} variant="outline">
      {status}
    </Badge>
  )
}
