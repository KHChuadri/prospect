'use client'

import Link from 'next/link'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { GripVertical } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { StatusBadge } from './StatusBadge'
import type { JobApplication } from '@/lib/types'

export function ApplicationCard({ application }: { application: JobApplication }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: application.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  }

  return (
    <Card
      ref={setNodeRef}
      style={style}
      className="group flex gap-2 p-3 transition-shadow duration-200 hover:shadow-md"
    >
      <button
        type="button"
        className="-ml-1 cursor-grab touch-none rounded text-muted-foreground/50 transition-colors hover:text-muted-foreground focus-visible:outline-2 focus-visible:outline-ring active:cursor-grabbing"
        aria-label={`Drag ${application.company} card`}
        {...attributes}
        {...listeners}
      >
        <GripVertical className="size-4" aria-hidden />
      </button>

      <div className="min-w-0 flex-1">
        <Link
          href={`/applications/${application.id}`}
          className="block truncate font-medium hover:underline"
        >
          {application.company}
        </Link>
        <p className="truncate text-sm text-muted-foreground">{application.role}</p>
        <div className="mt-2 flex items-center justify-between gap-2">
          <StatusBadge status={application.status} />
          {application.source && (
            <span className="truncate text-xs text-muted-foreground">{application.source}</span>
          )}
        </div>
      </div>
    </Card>
  )
}
