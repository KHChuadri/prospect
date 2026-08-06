import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { usersApi } from '@/lib/api'
import { EVENTS_KEY } from '@/hooks/useEvents'

export const ME_KEY = ['me'] as const

export function useMe() {
  return useQuery({
    queryKey: ME_KEY,
    queryFn: () => usersApi.me().then((r) => r.data),
  })
}

// Changing the city changes which events are visible, so the events list has
// to be refetched alongside the profile.
export function useUpdateCity() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (city: string | null) => usersApi.updateCity(city).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ME_KEY })
      qc.invalidateQueries({ queryKey: EVENTS_KEY })
    },
  })
}
