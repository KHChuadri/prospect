import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useMoveApplication } from '@/hooks/useApplications'
import type { ReactNode } from 'react'

function wrapper(client: QueryClient) {
  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
  return Wrapper
}

describe('useMoveApplication', () => {
  it('returns the updated application from the status endpoint', async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const { result } = renderHook(() => useMoveApplication(), { wrapper: wrapper(client) })

    result.current.mutate({ id: 1, newStatus: 'Screening' })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    // MSW handler returns mockApplication with status 'Screening'
    expect(result.current.data?.status).toBe('Screening')
  })
})
