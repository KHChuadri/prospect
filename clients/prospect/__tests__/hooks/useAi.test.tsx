import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useExtract, useMatch, useResume } from '@/hooks/useAi'

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

test('useExtract returns extracted fields', async () => {
  const { result } = renderHook(() => useExtract(), { wrapper })
  const data = await result.current.mutateAsync('some job posting')
  expect(data.company).toBe('Acme Corp')
  expect(data.ok).toBe(true)
})

test('useResume reads the stored résumé', async () => {
  const { result } = renderHook(() => useResume(), { wrapper })
  await waitFor(() => expect(result.current.data?.text).toBe('my stored résumé'))
})

test('useMatch returns a score', async () => {
  const { result } = renderHook(() => useMatch(5), { wrapper })
  const data = await result.current.mutateAsync(undefined)
  expect(data.score).toBe(72)
  expect(data.missing).toContain('Docker')
})
