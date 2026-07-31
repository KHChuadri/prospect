'use client'

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Card } from '@/components/ui/card'
import {
  applicationsByMonth,
  countByStatus,
  funnelStats,
  STATUS_COLORS,
} from '@/lib/analytics'
import { APPLICATION_STATUSES, type JobApplication } from '@/lib/types'

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card className="p-4">
      <h3 className="mb-4 text-sm font-semibold">{title}</h3>
      <div className="h-64 w-full">{children}</div>
    </Card>
  )
}

export function StatusBarChart({ applications }: { applications: JobApplication[] }) {
  const counts = countByStatus(applications)
  const data = APPLICATION_STATUSES.map((status) => ({ status, count: counts[status] }))
  return (
    <ChartCard title="Applications by status">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: -16 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
          <XAxis dataKey="status" tick={{ fontSize: 12 }} interval={0} angle={-20} textAnchor="end" height={50} />
          <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
          <Tooltip cursor={{ fill: '#0369a10d' }} />
          <Bar dataKey="count" radius={[6, 6, 0, 0]}>
            {data.map((d) => (
              <Cell key={d.status} fill={STATUS_COLORS[d.status]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  )
}

export function PipelineFunnel({ applications }: { applications: JobApplication[] }) {
  const f = funnelStats(applications)
  const stages = [
    { label: 'Applied', value: f.total, color: STATUS_COLORS.Applied },
    { label: 'Screening', value: f.screened, color: STATUS_COLORS.Screening },
    { label: 'Interviewing', value: f.interviewing, color: STATUS_COLORS.Interviewing },
    { label: 'Offer', value: f.offers, color: STATUS_COLORS.Offer },
  ]
  return (
    <ChartCard title="Pipeline funnel">
      <div className="flex h-full flex-col justify-center gap-3">
        {stages.map((s) => {
          const widthPct = f.total === 0 ? 0 : Math.round((s.value / f.total) * 100)
          return (
            <div key={s.label} className="flex items-center gap-3">
              <span className="w-24 shrink-0 text-sm text-muted-foreground">{s.label}</span>
              <div className="h-7 flex-1 overflow-hidden rounded-md bg-muted">
                <div
                  className="flex h-full items-center justify-end rounded-md px-2 text-xs font-medium text-white transition-[width] duration-500"
                  style={{ width: `${Math.max(widthPct, 8)}%`, backgroundColor: s.color }}
                >
                  {s.value}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </ChartCard>
  )
}

export function ActivityChart({ applications }: { applications: JobApplication[] }) {
  const data = applicationsByMonth(applications)
  return (
    <ChartCard title="Applications over time">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: -16 }}>
          <defs>
            <linearGradient id="activityFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#0ea5e9" stopOpacity={0.4} />
              <stop offset="100%" stopColor="#0ea5e9" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
          <XAxis dataKey="month" tick={{ fontSize: 12 }} />
          <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Area
            type="monotone"
            dataKey="count"
            stroke="#0369a1"
            strokeWidth={2}
            fill="url(#activityFill)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </ChartCard>
  )
}
