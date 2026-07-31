import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { applicationsApi } from '@/lib/api'
import type {
  ApplicationStatus,
  CreateApplicationInput,
  JobApplication,
  UpdateApplicationInput,
} from '@/lib/types'

export const APPS_KEY = ['applications'] as const

export function useApplications(status?: ApplicationStatus) {
  return useQuery({
    queryKey: [...APPS_KEY, status],
    queryFn: () => applicationsApi.getAll(status).then((r) => r.data),
  })
}

export function useCreateApplication() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (dto: CreateApplicationInput) => applicationsApi.create(dto).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: APPS_KEY }),
  })
}

export function useUpdateApplication(id: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (dto: UpdateApplicationInput) => applicationsApi.update(id, dto).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: APPS_KEY })
      qc.invalidateQueries({ queryKey: [...APPS_KEY, id] })
    },
  })
}

export function useDeleteApplication() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => applicationsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: APPS_KEY }),
  })
}

export function useUpdateStatus(id: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (newStatus: ApplicationStatus) =>
      applicationsApi.updateStatus(id, newStatus).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: APPS_KEY })
      qc.invalidateQueries({ queryKey: [...APPS_KEY, id] })
    },
  })
}

// Board drag: move any application by id with an optimistic cache update so the
// card snaps to its new column instantly. Targets the unfiltered list key the
// kanban board reads from.
export function useMoveApplication() {
  const qc = useQueryClient()
  const listKey = [...APPS_KEY, undefined] as const
  return useMutation({
    mutationFn: ({ id, newStatus }: { id: number; newStatus: ApplicationStatus }) =>
      applicationsApi.updateStatus(id, newStatus).then((r) => r.data),
    onMutate: async ({ id, newStatus }) => {
      await qc.cancelQueries({ queryKey: APPS_KEY })
      const prev = qc.getQueryData<JobApplication[]>(listKey)
      qc.setQueryData<JobApplication[]>(listKey, (old) =>
        old?.map((a) => (a.id === id ? { ...a, status: newStatus } : a)),
      )
      return { prev }
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) qc.setQueryData(listKey, ctx.prev)
    },
    onSettled: () => qc.invalidateQueries({ queryKey: APPS_KEY }),
  })
}
