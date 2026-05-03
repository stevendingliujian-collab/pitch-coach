import { api } from './index'

export interface ReviewComment {
  id: number
  timestamp_sec: number
  comment_text: string
  is_highlight: boolean
  reviewer_id: number
  mentioned_users: number[] | null
  created_at: string
}

export interface PendingReview {
  rehearsal_id: number
  pitch_task_id: number
  task_name: string
  user_id: number
  total_score: number | null
  audio_duration: number
  audio_url: string | null
  bid_date: string | null
  urgent: boolean
  submitted_at: string | null
}

export interface Certification {
  cert_id: number
  status: number
  status_label: string
  review_comment: string | null
  certified_at: string | null
}

export const reviewApi = {
  addComment: (rehearsalId: number, data: {
    timestamp_sec: number; comment_text: string; is_highlight?: boolean; mentioned_user_ids?: number[]
  }) => api.post<ReviewComment>(`/rehearsals/${rehearsalId}/comments`, data),

  listComments: (rehearsalId: number) =>
    api.get<ReviewComment[]>(`/rehearsals/${rehearsalId}/comments`),

  deleteComment: (rehearsalId: number, commentId: number) =>
    api.delete(`/rehearsals/${rehearsalId}/comments/${commentId}`),

  submitForReview: (rehearsalId: number) =>
    api.post(`/rehearsals/${rehearsalId}/submit-review`),

  listPending: () => api.get<PendingReview[]>('/reviews/pending'),

  certify: (data: { rehearsal_id: number; pitch_task_id: number; user_id: number; decision: string; comment?: string }) =>
    api.post('/certifications', data),

  getCertification: (pitchTaskId: number) =>
    api.get<Certification>(`/certifications/${pitchTaskId}`),
}
