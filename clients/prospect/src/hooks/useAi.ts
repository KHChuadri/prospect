import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { aiApi, uploadToPresignedUrl } from '@/lib/api'

export const RESUME_KEY = ['resume'] as const
export const MAX_RESUME_BYTES = 5 * 1024 * 1024

export function useExtract() {
  return useMutation({
    mutationFn: (text: string) => aiApi.extract(text).then((r) => r.data),
  })
}

export function useResume() {
  return useQuery({
    queryKey: RESUME_KEY,
    queryFn: () => aiApi.getResume().then((r) => r.data),
  })
}

export function useSaveResume() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (text: string) => aiApi.putResume(text).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: RESUME_KEY }),
  })
}

export function useUploadResume() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (file: File) => {
      const { data: slot } = await aiApi.resumeUploadUrl(file.name, file.type, file.size)
      await uploadToPresignedUrl(slot.url, file)
      const { data } = await aiApi.resumeIngest(slot.key, file.name)
      return data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: RESUME_KEY }),
  })
}

export function useMatch(appId: number) {
  return useMutation({
    mutationFn: (refresh?: boolean) => aiApi.match(appId, refresh ?? false).then((r) => r.data),
  })
}

export function useOptimize(appId: number) {
  return useMutation({
    mutationFn: (refresh?: boolean) =>
      aiApi.optimize(appId, refresh ?? false).then((r) => r.data.optimized_resume),
  })
}
