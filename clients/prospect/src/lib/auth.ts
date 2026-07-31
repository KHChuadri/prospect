// Callers: api.ts (interceptors), AppLayout (auth guard), login/register pages
export const getToken = (): string | null =>
  typeof window !== 'undefined' ? localStorage.getItem('accessToken') : null

export const getRefreshToken = (): string | null =>
  typeof window !== 'undefined' ? localStorage.getItem('refreshToken') : null

export const setTokens = (accessToken: string, refreshToken: string): void => {
  localStorage.setItem('accessToken', accessToken)
  localStorage.setItem('refreshToken', refreshToken)
}

export const clearTokens = (): void => {
  localStorage.removeItem('accessToken')
  localStorage.removeItem('refreshToken')
}

export const isAuthenticated = (): boolean => !!getToken()
