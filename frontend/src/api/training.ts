import { api } from './index'

export interface TrainingPlan {
  id: number
  tenant_id: number
  user_id: number
  pitch_task_id: number
  plan_id: number | null
  first_practice_date: string | null
  bid_date: string | null
  schedule_dates: string[] | null
  created_at: string
}

export interface TrainingSession {
  id: number
  plan_id: number
  mode: 'follow' | 'recite'
  page_number: number
  total_score: number | null
  dimension_scores: Record<string, number> | null
  feedback: string[] | null
  practice_date: string
  created_at: string
}

export interface SubmitSessionRequest {
  plan_id: number
  mode: 'follow' | 'recite'
  page_number: number
  transcript: string
  audio_url?: string
  duration_sec?: number
}

export const trainingApi = {
  createOrGetPlan(pitchTaskId: number, planId?: number) {
    return api.post<TrainingPlan>('/training/plans', null, {
      params: { pitch_task_id: pitchTaskId, plan_id: planId },
    })
  },

  listPlans(pitchTaskId?: number) {
    return api.get<TrainingPlan[]>('/training/plans', {
      params: pitchTaskId ? { pitch_task_id: pitchTaskId } : undefined,
    })
  },

  getPlan(planId: number) {
    return api.get<TrainingPlan>(`/training/plans/${planId}`)
  },

  getToday() {
    return api.get<{ plan_id: number; pitch_task_id: number; sessions_done_today: number; next_date: string | null }[]>(
      '/training/today'
    )
  },

  submitSession(data: SubmitSessionRequest) {
    return api.post<TrainingSession>('/training/sessions', data)
  },

  listSessions(params?: { plan_id?: number; pitch_task_id?: number }) {
    return api.get<TrainingSession[]>('/training/sessions', { params })
  },

  previewSchedule(firstDate: string, bidDate?: string) {
    return api.get<string[]>('/training/schedule/preview', {
      params: { first_date: firstDate, bid_date: bidDate },
    })
  },
}
