import type { LucideIcon } from 'lucide-react'
import { Card } from '@/components/ui/card'

export function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  accent,
}: {
  label: string
  value: string | number
  sub?: string
  icon?: LucideIcon
  accent?: string
}) {
  return (
    <Card className="flex items-start gap-3 p-4">
      {Icon && (
        <span
          className="flex size-9 shrink-0 items-center justify-center rounded-lg"
          style={{ backgroundColor: accent ? `${accent}1a` : undefined, color: accent }}
          aria-hidden
        >
          <Icon className="size-5" />
        </span>
      )}
      <div className="min-w-0">
        <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">{label}</p>
        <p className="font-mono text-2xl font-bold tracking-tight tabular-nums">{value}</p>
        {sub && <p className="text-xs text-muted-foreground">{sub}</p>}
      </div>
    </Card>
  )
}
