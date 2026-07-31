'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useApplications } from '@/hooks/useApplications'
import { ApplicationTable } from '@/components/applications/ApplicationTable'
import { KanbanBoard } from '@/components/applications/KanbanBoard'
import { ViewToggle, type DashboardView } from '@/components/applications/ViewToggle'
import { Button } from '@/components/ui/button'

export default function DashboardPage() {
  const [view, setView] = useState<DashboardView>('board')
  const { data: all = [], isLoading } = useApplications()

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold tracking-tight">Applications</h1>
        <div className="flex items-center gap-2">
          <ViewToggle value={view} onChange={setView} />
          <Button nativeButton={false} render={<Link href="/applications/new" />}>+ Add application</Button>
        </div>
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-32 animate-pulse rounded-xl bg-muted" />
          ))}
        </div>
      ) : view === 'board' ? (
        <KanbanBoard applications={all} />
      ) : (
        <ApplicationTable applications={all} />
      )}
    </div>
  )
}
