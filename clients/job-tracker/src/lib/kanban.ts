// Maps a dnd-kit drag (active card + whatever it was dropped over) to a status
// change, or null when nothing should change. Kept pure so it is unit-testable
// without simulating pointer drag.
import type { ApplicationStatus, JobApplication } from './types'
import { APPLICATION_STATUSES } from './types'

const isStatus = (v: unknown): v is ApplicationStatus =>
  typeof v === 'string' && (APPLICATION_STATUSES as string[]).includes(v)

export function resolveDrop(
  activeId: number,
  overId: string | number | null,
  apps: JobApplication[],
): { id: number; newStatus: ApplicationStatus } | null {
  if (overId == null) return null
  const active = apps.find((a) => a.id === activeId)
  if (!active) return null

  const target: ApplicationStatus | undefined = isStatus(overId)
    ? overId
    : apps.find((a) => a.id === Number(overId))?.status

  if (!target || target === active.status) return null
  return { id: activeId, newStatus: target }
}
