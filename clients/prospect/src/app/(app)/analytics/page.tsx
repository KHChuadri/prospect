'use client'

import { Briefcase, CalendarCheck, Trophy, XCircle } from 'lucide-react'
import { useApplications } from '@/hooks/useApplications'
import { funnelStats, STATUS_COLORS } from '@/lib/analytics'
import { StatCard } from '@/components/analytics/StatCard'
import {
  ActivityChart,
  PipelineFunnel,
  StatusBarChart,
} from '@/components/analytics/AnalyticsCharts'

export default function AnalyticsPage() {
  const { data: all = [], isLoading } = useApplications()
  const f = funnelStats(all)

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Analytics</h1>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-xl bg-muted" />
          ))}
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Total applications"
              value={f.total}
              icon={Briefcase}
              accent={STATUS_COLORS.Applied}
            />
            <StatCard
              label="Interview rate"
              value={`${f.interviewRate}%`}
              sub={`${f.interviewing} reached interview`}
              icon={CalendarCheck}
              accent={STATUS_COLORS.Interviewing}
            />
            <StatCard
              label="Offers"
              value={f.offers}
              sub={`${f.offerRate}% offer rate`}
              icon={Trophy}
              accent={STATUS_COLORS.Offer}
            />
            <StatCard
              label="Rejected"
              value={f.rejected}
              icon={XCircle}
              accent={STATUS_COLORS.Rejected}
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <StatusBarChart applications={all} />
            <PipelineFunnel applications={all} />
          </div>

          <ActivityChart applications={all} />
        </>
      )}
    </div>
  )
}
