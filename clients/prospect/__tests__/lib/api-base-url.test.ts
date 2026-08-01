// Regression: the containerised build sets NEXT_PUBLIC_API_URL=/api (Dockerfile,
// docker-compose.yml) so the bundle talks to Caddy same-origin. Every call site
// here ALSO hard-coded /api, so the browser requested /api/api/auth/login and
// Caddy 404'd every backend route — login was just the first one users hit.
//
// Nothing in the suite caught it: the MSW mocks only ever ran with an
// origin-style base (http://localhost:5135), where the doubling can't happen.
// These tests pin the deployed value specifically.
import type { AxiosInstance, AxiosStatic, InternalAxiosRequestConfig } from 'axios'

const DEPLOYED_BASE = '/api'
const LOCAL_BASE = 'http://localhost:5135/api'

// resetModules gives src/lib/api.ts a fresh axios instance, so the bare `axios`
// the refresh path calls must be pulled from the same registry — a top-level
// import would be a different copy and any spy on it would silently miss.
async function loadApi(baseUrl: string) {
  jest.resetModules()
  process.env.NEXT_PUBLIC_API_URL = baseUrl
  const axios = ((await import('axios')) as unknown as { default: AxiosStatic }).default
  return { ...(await import('@/lib/api')), axios }
}

// Swaps in an adapter that records the URL axios actually composed (baseURL +
// path, via axios's own buildFullPath) and short-circuits the network.
function recordUrls(api: AxiosInstance): string[] {
  const seen: string[] = []
  api.defaults.adapter = async (config: InternalAxiosRequestConfig) => {
    seen.push(api.getUri({ url: config.url }))
    return {
      data: {},
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    } as never
  }
  return seen
}

describe('API URL composition', () => {
  const original = process.env.NEXT_PUBLIC_API_URL

  afterEach(() => {
    process.env.NEXT_PUBLIC_API_URL = original
    localStorage.clear()
  })

  it('does not double the /api prefix under the container config', async () => {
    const { api, authApi } = await loadApi(DEPLOYED_BASE)
    const seen = recordUrls(api)

    await authApi.login('user@example.com', 'pw')

    expect(seen).toEqual(['/api/auth/login'])
    expect(seen[0]).not.toContain('/api/api')
  })

  it('composes every backend route against the base exactly once', async () => {
    const { api, authApi, applicationsApi, notesApi } = await loadApi(DEPLOYED_BASE)
    const seen = recordUrls(api)

    await authApi.register('user@example.com', 'pw')
    await authApi.revoke()
    await applicationsApi.getAll()
    await applicationsApi.getById(7)
    await applicationsApi.updateStatus(7, 'Applied')
    await notesApi.getAll(7)

    expect(seen).toEqual([
      '/api/auth/register',
      '/api/auth/revoke',
      '/api/applications',
      '/api/applications/7',
      '/api/applications/7/status',
      '/api/applications/7/notes',
    ])
    expect(seen.filter((u) => u.includes('/api/api'))).toEqual([])
  })

  it('still resolves to an absolute URL for local dev', async () => {
    const { api, authApi } = await loadApi(LOCAL_BASE)
    const seen = recordUrls(api)

    await authApi.login('user@example.com', 'pw')

    expect(seen).toEqual(['http://localhost:5135/api/auth/login'])
  })

  // The refresh call builds its URL by string concatenation instead of going
  // through the axios instance, so it can break independently. With a base of
  // "/" it would produce "//auth/refresh" — a protocol-relative URL pointing at
  // a host named "auth" rather than a same-origin path.
  it('sends token refresh to a same-origin path, not a protocol-relative URL', async () => {
    const { api, axios } = await loadApi(DEPLOYED_BASE)
    localStorage.setItem('refreshToken', 'stored-refresh-token')

    const post = jest.spyOn(axios, 'post').mockResolvedValue({
      data: { accessToken: 'new-access', refreshToken: 'new-refresh' },
    })

    api.defaults.adapter = async (config: InternalAxiosRequestConfig) => {
      if (config.headers?.Authorization === 'Bearer new-access') {
        return { data: {}, status: 200, statusText: 'OK', headers: {}, config } as never
      }
      throw Object.assign(new Error('Unauthorized'), {
        config,
        response: { status: 401 },
      })
    }

    await api.get('/applications')

    const refreshUrl = post.mock.calls[0][0] as string
    expect(refreshUrl).toBe('/api/auth/refresh')
    expect(refreshUrl.startsWith('//')).toBe(false)

    post.mockRestore()
  })
})
