export type ApplicationStatus =
  | 'Applied'
  | 'Screening'
  | 'Interviewing'
  | 'Offer'
  | 'Rejected'
  | 'Withdrawn'

export const APPLICATION_STATUSES: ApplicationStatus[] = [
  'Applied', 'Screening', 'Interviewing', 'Offer', 'Rejected', 'Withdrawn',
]

export interface StatusTransition {
  id: number
  applicationId: number
  fromStatus: ApplicationStatus
  toStatus: ApplicationStatus
  transitionedAt: string
}

export interface Note {
  id: number
  applicationId: number
  content: string
  createdAt: string
}

export interface JobApplication {
  id: number
  userId: number
  company: string
  role: string
  status: ApplicationStatus
  source: string | null
  salaryRange: string | null
  appliedAt: string
  notes: Note[]
  statusTransitions: StatusTransition[]
}

export interface AuthResponse {
  accessToken: string
  refreshToken: string
}

export interface CreateApplicationInput {
  company: string
  role: string
  source?: string
  salaryRange?: string
}

export interface UpdateApplicationInput {
  company?: string
  role?: string
  source?: string
  salaryRange?: string
}

export type FollowUpStatus = 'pending' | 'approved' | 'rejected' | 'sent'

export interface FollowUp {
  id: number
  app_id: number
  user_id: number
  thread_id: string
  status: FollowUpStatus
  draft_subject: string
  draft_body: string
  recipient_email: string | null
  reason: string
  created_at: string
  sent_at: string | null
}

export interface Extraction {
  company: string
  role: string
  location: string | null
  salary: string | null
  requirements: string[]
  ok: boolean
}

export interface MatchResult {
  score: number
  missing: string[]
  matched: string[]
  suggestions: string[]
}

export type RecommendationStatus = 'pending' | 'accepted' | 'dismissed'

export interface Recommendation {
  id: number
  user_id: number
  source_message_id: string
  source_sender: string
  company: string
  role: string
  location: string | null
  url: string | null
  raw_snippet: string
  status: RecommendationStatus
  accepted_application_id: number | null
  created_at: string
}
