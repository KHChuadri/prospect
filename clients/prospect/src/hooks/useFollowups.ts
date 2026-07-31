import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { followupsApi } from '@/lib/api'
import type { FollowUp } from '@/lib/types'

export const FOLLOWUPS_KEY = ['followups'] as const

export function useFollowups(status: FollowUp['status'] = 'pending') {
  return useQuery({
    queryKey: [...FOLLOWUPS_KEY, status],
    queryFn: () => followupsApi.list(status).then((r) => r.data),
  })
}

export function useApproveFollowup() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, recipientEmail, subject, body }: {
      id: number; recipientEmail: string; subject?: string; body?: string
    }) => followupsApi.approve(id, recipientEmail, subject, body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: FOLLOWUPS_KEY }),
  })
}

export function useRejectFollowup() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => followupsApi.reject(id).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: FOLLOWUPS_KEY }),
  })
}
