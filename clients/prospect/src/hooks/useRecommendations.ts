import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { applicationsApi, recommendationsApi } from '@/lib/api'
import type { Recommendation } from '@/lib/types'

export const RECOMMENDATIONS_KEY = ['recommendations'] as const

export function useRecommendations() {
  return useQuery({
    queryKey: RECOMMENDATIONS_KEY,
    queryFn: () => recommendationsApi.list('pending').then((r) => r.data),
  })
}

const norm = (s: string) => s.trim().toLowerCase()

// Accept is client-orchestrated: create the JobApplication in .NET first,
// then mark the recommendation accepted in the agent with the new app id.
// If a prior attempt already created the app (accept failed after create),
// a retry reuses the existing company+role match instead of creating a
// duplicate — .NET's create is not idempotent.
export function useAcceptRecommendation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (rec: Recommendation) => {
      const { data: existing } = await applicationsApi.getAll()
      const app =
        existing.find(
          (a) => norm(a.company) === norm(rec.company) && norm(a.role) === norm(rec.role),
        ) ??
        (
          await applicationsApi.create({
            company: rec.company,
            role: rec.role,
            source: rec.source_sender || 'Email',
          })
        ).data
      await recommendationsApi.accept(rec.id, app.id)
      return app
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: RECOMMENDATIONS_KEY }),
  })
}

export function useDismissRecommendation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => recommendationsApi.dismiss(id).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: RECOMMENDATIONS_KEY }),
  })
}
