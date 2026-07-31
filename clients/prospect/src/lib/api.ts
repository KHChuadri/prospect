// Callers: all hooks (useApplications, useNotes), login/register pages
import axios from 'axios'
import type {
  AuthResponse,
  ApplicationStatus,
  CreateApplicationInput,
  Extraction,
  FollowUp,
  JobApplication,
  MatchResult,
  Note,
  Recommendation,
  UpdateApplicationInput,
} from './types'
import { clearTokens, getRefreshToken, getToken, setTokens } from './auth'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:5135'

export const api = axios.create({ baseURL: BASE_URL })

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

let isRefreshing = false
let waitQueue: Array<(token: string) => void> = []

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status !== 401 || original._retry) throw error

    original._retry = true

    if (isRefreshing) {
      return new Promise((resolve) => {
        waitQueue.push((token) => {
          original.headers.Authorization = `Bearer ${token}`
          resolve(api(original))
        })
      })
    }

    isRefreshing = true
    const refreshToken = getRefreshToken()

    if (!refreshToken) {
      clearTokens()
      if (typeof window !== 'undefined') window.location.href = '/login'
      throw error
    }

    try {
      const { data } = await axios.post<AuthResponse>(
        `${BASE_URL}/api/auth/refresh`,
        JSON.stringify(refreshToken), // backend expects raw JSON string
        { headers: { 'Content-Type': 'application/json' } },
      )
      setTokens(data.accessToken, data.refreshToken)
      waitQueue.forEach((cb) => cb(data.accessToken))
      waitQueue = []
      original.headers.Authorization = `Bearer ${data.accessToken}`
      return api(original)
    } catch {
      clearTokens()
      if (typeof window !== 'undefined') window.location.href = '/login'
      throw error
    } finally {
      isRefreshing = false
    }
  },
)

export const authApi = {
  register: (email: string, password: string) =>
    api.post<AuthResponse>('/api/auth/register', { email, password }),
  login: (email: string, password: string) =>
    api.post<AuthResponse>('/api/auth/login', { email, password }),
  revoke: () => api.post('/api/auth/revoke'),
}

export const applicationsApi = {
  getAll: (status?: ApplicationStatus) =>
    api.get<JobApplication[]>('/api/applications', {
      params: status ? { status } : undefined,
    }),
  getById: (id: number) => api.get<JobApplication>(`/api/applications/${id}`),
  create: (dto: CreateApplicationInput) =>
    api.post<JobApplication>('/api/applications', dto),
  update: (id: number, dto: UpdateApplicationInput) =>
    api.patch<JobApplication>(`/api/applications/${id}`, dto),
  delete: (id: number) => api.delete(`/api/applications/${id}`),
  updateStatus: (id: number, newStatus: ApplicationStatus) =>
    api.patch<JobApplication>(`/api/applications/${id}/status`, { newStatus }),
}

export const notesApi = {
  getAll: (applicationId: number) =>
    api.get<Note[]>(`/api/applications/${applicationId}/notes`),
  create: (applicationId: number, content: string) =>
    api.post<Note>(`/api/applications/${applicationId}/notes`, { content }),
}

const AGENT_URL = process.env.NEXT_PUBLIC_AGENT_URL ?? 'http://localhost:8000'

export const agentApi = axios.create({ baseURL: AGENT_URL })
agentApi.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export const followupsApi = {
  list: (status: FollowUp['status'] = 'pending') =>
    agentApi.get<FollowUp[]>('/follow-ups', { params: { status } }),
  approve: (id: number, recipientEmail: string, subject?: string, body?: string) =>
    agentApi.post<FollowUp>(`/follow-ups/${id}/approve`, {
      recipient_email: recipientEmail, subject, body,
    }),
  reject: (id: number) => agentApi.post<FollowUp>(`/follow-ups/${id}/reject`),
}

export const aiApi = {
  extract: (text: string) => agentApi.post<Extraction>('/ai/extract', { text }),
  getResume: () => agentApi.get<{ text: string }>('/ai/resume'),
  putResume: (text: string) => agentApi.put<{ ok: boolean }>('/ai/resume', { text }),
  putJd: (appId: number, text: string) =>
    agentApi.put<{ ok: boolean }>(`/ai/apps/${appId}/jd`, { text }),
  match: (appId: number, refresh = false) =>
    agentApi.post<MatchResult>(`/ai/match/${appId}`, null, { params: { refresh } }),
  optimize: (appId: number, refresh = false) =>
    agentApi.post<{ optimized_resume: string }>(`/ai/optimize/${appId}`, null, { params: { refresh } }),
}

export const recommendationsApi = {
  list: (status: Recommendation['status'] = 'pending') =>
    agentApi.get<Recommendation[]>('/recommendations', { params: { status } }),
  accept: (id: number, applicationId: number) =>
    agentApi.post<Recommendation>(`/recommendations/${id}/accept`, {
      application_id: applicationId,
    }),
  dismiss: (id: number) =>
    agentApi.post<Recommendation>(`/recommendations/${id}/dismiss`),
}
