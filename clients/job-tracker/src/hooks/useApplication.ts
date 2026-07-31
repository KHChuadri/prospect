import { useQuery } from '@tanstack/react-query'
import { applicationsApi } from '@/lib/api'
import { APPS_KEY } from './useApplications'

export function useApplication(id: number) {
  return useQuery({
    queryKey: [...APPS_KEY, id],
    queryFn: () => applicationsApi.getById(id).then((r) => r.data),
    enabled: id > 0,
  })
}
