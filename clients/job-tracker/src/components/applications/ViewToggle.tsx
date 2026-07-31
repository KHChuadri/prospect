'use client'

import { LayoutGrid, Table2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

export type DashboardView = 'board' | 'table'

export function ViewToggle({
  value,
  onChange,
}: {
  value: DashboardView
  onChange: (v: DashboardView) => void
}) {
  return (
    <div className="inline-flex rounded-lg border bg-background p-0.5" role="group" aria-label="View">
      <Button
        size="sm"
        variant={value === 'board' ? 'default' : 'ghost'}
        onClick={() => onChange('board')}
        aria-pressed={value === 'board'}
      >
        <LayoutGrid /> Board
      </Button>
      <Button
        size="sm"
        variant={value === 'table' ? 'default' : 'ghost'}
        onClick={() => onChange('table')}
        aria-pressed={value === 'table'}
      >
        <Table2 /> Table
      </Button>
    </div>
  )
}
