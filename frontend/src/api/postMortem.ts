import { api } from './index'

export interface PostMortemSummary {
  id: number
  pitch_task_id: number
  status: 'pending' | 'processing' | 'completed' | 'failed'
  question_count: number | null
  our_talk_ratio: number | null
  prediction_hit_rate: number | null
  overall_score: number | null
  grade: string | null
  created_at: string
  updated_at: string
  error_msg: string | null
}

export interface EvaluatorQuestion {
  id: number
  category: string
  category_name: string
  question: string
  answer_text: string
  answer_quality: number
  question_type: string
  notes: string
  is_risky: boolean
}

export interface AnswerAssessment {
  question_id: number
  score: number
  feedback: string
  suggestion: string
  reference_from_kb: string
  ideal_answer_outline: string
}

export interface KeyMoment {
  type: 'highlight' | 'pressure' | 'turning_point' | 'missed'
  speaker: string
  text: string
  analysis: string
  importance: number
}

export interface Insights {
  overall_score: number
  grade: string
  strengths: string[]
  weaknesses: string[]
  top_risks: string[]
  action_items: Array<{ priority: 'high' | 'medium'; action: string; deadline: string }>
  prediction_summary: string
  next_rehearsal_focus: string[]
}

export interface PostMortemReport extends PostMortemSummary {
  evaluator_count: number | null
  question_categories: Record<string, number> | null
  evaluator_questions: EvaluatorQuestion[]
  answer_assessments: AnswerAssessment[]
  key_moments: KeyMoment[]
  insights: Insights | null
  followup_draft: string | null
  diarization_segment_count: number
}

export const postMortemApi = {
  create: (taskId: number, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post<PostMortemSummary>(`/post-mortem/${taskId}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  list: (taskId: number) => api.get<PostMortemSummary[]>(`/post-mortem/${taskId}`),
  get: (pmId: number) => api.get<PostMortemReport>(`/post-mortem/reports/${pmId}`),
  delete: (pmId: number) => api.delete(`/post-mortem/reports/${pmId}`),
  getFollowup: (pmId: number) =>
    api.get<{ id: number; followup_draft: string; pitch_task_id: number }>(
      `/post-mortem/reports/${pmId}/followup`
    ),
  retry: (pmId: number) => api.post(`/post-mortem/reports/${pmId}/retry`),
}
