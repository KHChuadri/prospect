import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { notesApi } from '@/lib/api'

const notesKey = (applicationId: number) => ['notes', applicationId] as const

export function useNotes(applicationId: number) {
  return useQuery({
    queryKey: notesKey(applicationId),
    queryFn: () => notesApi.getAll(applicationId).then((r) => r.data),
    enabled: applicationId > 0,
  })
}

export function useCreateNote(applicationId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (content: string) => notesApi.create(applicationId, content).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: notesKey(applicationId) }),
  })
}
