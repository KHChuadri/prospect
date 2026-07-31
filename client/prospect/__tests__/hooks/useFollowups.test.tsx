import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useFollowups } from '@/hooks/useFollowups'
import { followupsApi } from '@/lib/api'

jest.mock('../../src/lib/api', () => ({
  followupsApi: { list: jest.fn() },
}))

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

test('useFollowups returns pending list', async () => {
  ;(followupsApi.list as jest.Mock).mockResolvedValue({
    data: [{ id: 1, draft_subject: 'Hi', status: 'pending' }],
  })
  const { result } = renderHook(() => useFollowups(), { wrapper })
  await waitFor(() => expect(result.current.data).toHaveLength(1))
  expect(result.current.data?.[0].id).toBe(1)
})
