'use client'

import {
  DndContext,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
} from '@dnd-kit/core'
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable'
import { KanbanColumn } from './KanbanColumn'
import { useMoveApplication } from '@/hooks/useApplications'
import { resolveDrop } from '@/lib/kanban'
import { APPLICATION_STATUSES, type JobApplication } from '@/lib/types'

export function KanbanBoard({ applications }: { applications: JobApplication[] }) {
  const move = useMoveApplication()

  const sensors = useSensors(
    // 6px activation distance so clicking the card link doesn't start a drag.
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    const result = resolveDrop(Number(active.id), over?.id ?? null, applications)
    if (result) move.mutate(result)
  }

  return (
    <DndContext sensors={sensors} collisionDetection={closestCorners} onDragEnd={handleDragEnd}>
      <div className="flex gap-4 overflow-x-auto pb-4">
        {APPLICATION_STATUSES.map((status) => (
          <KanbanColumn
            key={status}
            status={status}
            applications={applications.filter((a) => a.status === status)}
          />
        ))}
      </div>
    </DndContext>
  )
}
