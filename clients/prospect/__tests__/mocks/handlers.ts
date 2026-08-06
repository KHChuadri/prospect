// MSW handlers — mock all backend endpoints for tests
import { http, HttpResponse } from 'msw'
import type { JobApplication, Note, Recommendation } from '@/lib/types'

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:5135/api'
const AGENT = process.env.NEXT_PUBLIC_AGENT_URL ?? 'http://localhost:8000'

export const mockApplication: JobApplication = {
  id: 1,
  userId: 1,
  company: 'Acme Corp',
  role: 'Software Engineer',
  status: 'Applied',
  source: 'LinkedIn',
  salaryRange: '80k-100k',
  appliedAt: '2024-01-15T00:00:00Z',
  notes: [],
  statusTransitions: [],
}

export const mockNote: Note = {
  id: 1,
  applicationId: 1,
  content: 'Great culture fit',
  createdAt: '2024-01-16T00:00:00Z',
}

export const mockRecommendation: Recommendation = {
  id: 1,
  user_id: 1,
  source_message_id: 'm1',
  source_sender: 'jobs@acme.com',
  company: 'Acme Corp',
  role: 'Backend Engineer',
  location: 'Remote',
  url: 'https://jobs.acme.com/1',
  raw_snippet: 'Acme is growing our engineering team…',
  status: 'pending',
  accepted_application_id: null,
  created_at: '2026-07-07T00:00:00Z',
}

export const handlers = [
  http.post(`${BASE}/auth/login`, () =>
    HttpResponse.json({ accessToken: 'access-tok', refreshToken: 'refresh-tok' }),
  ),
  http.post(`${BASE}/auth/register`, () =>
    HttpResponse.json({ accessToken: 'access-tok', refreshToken: 'refresh-tok' }, { status: 201 }),
  ),
  http.post(`${BASE}/auth/revoke`, () => new HttpResponse(null, { status: 204 })),
  http.get(`${BASE}/applications`, () => HttpResponse.json([mockApplication])),
  http.get(`${BASE}/applications/:id`, () => HttpResponse.json(mockApplication)),
  http.post(`${BASE}/applications`, () =>
    HttpResponse.json(mockApplication, { status: 201 }),
  ),
  http.patch(`${BASE}/applications/:id`, () => HttpResponse.json(mockApplication)),
  http.delete(`${BASE}/applications/:id`, () => new HttpResponse(null, { status: 204 })),
  http.patch(`${BASE}/applications/:id/status`, () =>
    HttpResponse.json({ ...mockApplication, status: 'Screening' }),
  ),
  http.get(`${BASE}/applications/:id/notes`, () => HttpResponse.json([mockNote])),
  http.post(`${BASE}/applications/:id/notes`, () =>
    HttpResponse.json(mockNote, { status: 201 }),
  ),
  http.post(`${AGENT}/ai/extract`, () =>
    HttpResponse.json({
      company: 'Acme Corp', role: 'Backend Engineer',
      location: 'Remote', salary: '120k-150k',
      requirements: ['Python', 'Postgres'], ok: true,
    }),
  ),
  http.get(`${AGENT}/ai/resume`, () =>
    HttpResponse.json({
      text: 'my stored résumé', profile: null,
      file_name: null, updated_at: null,
    }),
  ),
  http.post(`${AGENT}/ai/resume/upload-url`, () =>
    HttpResponse.json({ key: 'resumes/1/abc.pdf', url: 'https://bucket.test/abc.pdf?sig=x' }),
  ),
  http.put('https://bucket.test/abc.pdf', () => new HttpResponse(null, { status: 200 })),
  http.post(`${AGENT}/ai/resume/ingest`, () =>
    HttpResponse.json({
      text: 'JANE CHEN\nSenior Engineer',
      profile: {
        name: 'Jane Chen', email: 'jane@example.com', phone: null,
        location: 'Sydney', links: [], skills: ['Python', 'Postgres'],
        experience: [{
          company: 'Acme Corp', title: 'Senior Engineer',
          start: '2023', end: '2026', bullets: ['Built the billing pipeline.'],
        }],
        education: [{ school: 'UNSW', degree: 'BSc Computer Science', year: '2022' }],
      },
      warning: null,
    }),
  ),
  http.put(`${AGENT}/ai/resume`, () => HttpResponse.json({ ok: true })),
  http.put(`${AGENT}/ai/apps/:appId/jd`, () => HttpResponse.json({ ok: true })),
  http.post(`${AGENT}/ai/match/:appId`, () =>
    HttpResponse.json({
      score: 72, missing: ['Docker'], matched: ['Python', 'Postgres'],
      suggestions: ['Mention Docker experience'],
    }),
  ),
  http.post(`${AGENT}/ai/optimize/:appId`, () =>
    HttpResponse.json({ optimized_resume: 'TAILORED RÉSUMÉ TEXT' }),
  ),
  http.get(`${AGENT}/recommendations`, () => HttpResponse.json([mockRecommendation])),
  http.post(`${AGENT}/recommendations/:id/accept`, () =>
    HttpResponse.json({ ...mockRecommendation, status: 'accepted' }),
  ),
  http.post(`${AGENT}/recommendations/:id/dismiss`, () =>
    HttpResponse.json({ ...mockRecommendation, status: 'dismissed' }),
  ),
]
