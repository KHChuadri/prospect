// Tests: auth token helpers from src/lib/auth.ts
describe('auth helpers', () => {
  afterEach(() => localStorage.clear())

  it('setTokens writes both tokens to localStorage', async () => {
    const { setTokens, getToken } = await import('@/lib/auth')
    setTokens('acc', 'ref')
    expect(getToken()).toBe('acc')
  })

  it('clearTokens removes both keys', async () => {
    const { setTokens, clearTokens, getToken } = await import('@/lib/auth')
    setTokens('acc', 'ref')
    clearTokens()
    expect(getToken()).toBeNull()
  })
})
