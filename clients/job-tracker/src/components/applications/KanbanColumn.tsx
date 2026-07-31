'use client'

import { useDroppable } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { ApplicationCard } from './ApplicationCard'
import { STATUS_COLORS } from '@/lib/analytics'
import type { ApplicationStatus, JobApplication } from '@/lib/types'

export function KanbanColumn({
  status,
  applications,
}: {
  status: ApplicationStatus
  applications: JobApplication[]
}) {
  const { setNodeRef, isOver } = useDroppable({ id: status })

  return (
    <section
      aria-label={`${status} column`}
      className="flex w-72 shrink-0 flex-col rounded-xl bg-muted/40 p-3"
    >
      <header className="mb-3 flex items-center gap-2 px-1">
        <span
          className="size-2.5 rounded-full"
          style={{ backgroundColor: STATUS_COLORS[status] }}
          aria-hidden
        />
        <h2 className="text-sm font-semibold">{status}</h2>
        <span className="ml-auto rounded-full bg-background px-2 py-0.5 text-xs font-medium text-muted-foreground">
          {applications.length}
        </span>
      </header>

      <div
        ref={setNodeRef}
        className={`flex min-h-24 flex-1 flex-col gap-2 rounded-lg p-1 transition-colors duration-200 ${
          isOver ? 'bg-primary/5 ring-2 ring-primary/30' : ''
        }`}
      >
        <SortableContext
          items={applications.map((a) => a.id)}
          strategy={verticalListSortingStrategy}
        >
          {applications.map((app) => (
            <ApplicationCard key={app.id} application={app} />
          ))}
        </SortableContext>

        {applications.length === 0 && (
          <p className="px-2 py-6 text-center text-xs text-muted-foreground">Drop here</p>
        )}
      </div>
    </section>
  )
}
