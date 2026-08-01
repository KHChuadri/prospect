import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { eventsApi } from '@/lib/api'

export const EVENTS_KEY = ['events'] as const

export function useEvents(saved = false) {
  return useQuery({
    queryKey: [...EVENTS_KEY, { saved }],
    queryFn: () => eventsApi.list(saved).then((r) => r.data),
  })
}

// Both tabs invalidate together: marking interested moves an event out of the
// feed and into Saved, so a stale Saved list would be wrong.
function useEventDecision(fn: (id: number) => Promise<unknown>) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: () => qc.invalidateQueries({ queryKey: EVENTS_KEY }),
  })
}

export function useMarkInterested() {
  return useEventDecision((id) => eventsApi.interested(id).then((r) => r.data))
}

export function useDismissEvent() {
  return useEventDecision((id) => eventsApi.dismiss(id).then((r) => r.data))
}

export function useUndoEventDecision() {
  return useEventDecision((id) => eventsApi.undo(id).then((r) => r.data))
}
