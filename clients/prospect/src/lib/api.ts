// Callers: all hooks (useApplications, useNotes), login/register pages
import axios from 'axios'
import type {
  AuthResponse,
  ApplicationStatus,
  CreateApplicationInput,
  EventItem,
  Extraction,
  FollowUp,
  JobApplication,
  MatchResult,
  Note,
  Recommendation,
  ResumeIngestResult,
  StoredResume,
  UpdateApplicationInput,
} from './types'
import { clearTokens, getRefreshToken, getToken, setTokens } from './auth'

// Includes the /api prefix, so call sites below use bare paths — same shape as
// AGENT_URL further down. Keeps the prefix in exactly one place per service.
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:5135/api'

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
        `${BASE_URL}/auth/refresh`,
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
    api.post<AuthResponse>('/auth/register', { email, password }),
  login: (email: string, password: string) =>
    api.post<AuthResponse>('/auth/login', { email, password }),
  revoke: () => api.post('/auth/revoke'),
}

export const applicationsApi = {
  getAll: (status?: ApplicationStatus) =>
    api.get<JobApplication[]>('/applications', {
      params: status ? { status } : undefined,
    }),
  getById: (id: number) => api.get<JobApplication>(`/applications/${id}`),
  create: (dto: CreateApplicationInput) =>
    api.post<JobApplication>('/applications', dto),
  update: (id: number, dto: UpdateApplicationInput) =>
    api.patch<JobApplication>(`/applications/${id}`, dto),
  delete: (id: number) => api.delete(`/applications/${id}`),
  updateStatus: (id: number, newStatus: ApplicationStatus) =>
    api.patch<JobApplication>(`/applications/${id}/status`, { newStatus }),
}

export const notesApi = {
  getAll: (applicationId: number) =>
    api.get<Note[]>(`/applications/${applicationId}/notes`),
  create: (applicationId: number, content: string) =>
    api.post<Note>(`/applications/${applicationId}/notes`, { content }),
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
  getResume: () => agentApi.get<StoredResume>('/ai/resume'),
  putResume: (text: string) => agentApi.put<{ ok: boolean }>('/ai/resume', { text }),
  resumeUploadUrl: (filename: string, contentType: string, size: number) =>
    agentApi.post<{ key: string; url: string }>('/ai/resume/upload-url', {
      filename, content_type: contentType, size,
    }),
  resumeIngest: (key: string, filename: string) =>
    agentApi.post<ResumeIngestResult>('/ai/resume/ingest', { key, filename }),
  putJd: (appId: number, text: string) =>
    agentApi.put<{ ok: boolean }>(`/ai/apps/${appId}/jd`, { text }),
  match: (appId: number, refresh = false) =>
    agentApi.post<MatchResult>(`/ai/match/${appId}`, null, { params: { refresh } }),
  optimize: (appId: number, refresh = false) =>
    agentApi.post<{ optimized_resume: string }>(`/ai/optimize/${appId}`, null, { params: { refresh } }),
}

// Deliberately a bare axios call rather than `agentApi`: that instance's
// interceptor attaches an Authorization header, and a presigned URL already
// carries its own signature — R2 rejects a request that has both.
export const uploadToPresignedUrl = (url: string, file: File) =>
  axios.put(url, file, { headers: { 'Content-Type': file.type } })

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

export const eventsApi = {
  list: (saved = false) =>
    agentApi.get<EventItem[]>('/events', { params: { saved } }),
  interested: (id: number) => agentApi.post<EventItem>(`/events/${id}/interested`),
  dismiss: (id: number) => agentApi.post<EventItem>(`/events/${id}/dismiss`),
  undo: (id: number) => agentApi.delete<EventItem>(`/events/${id}/decision`),
}
