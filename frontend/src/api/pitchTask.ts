import { api } from './index'

export interface PitchTask {
  id: number
  name: string
  customer_name: string | null
  customer_industry: string | null
  budget: string | null
  bid_date: string | null
  bid_time_limit: number | null
  status: number
  result: number | null
  owner_id: number
  // extended fields (available from backend list response)
  created_at?: string | null
  page_count?: number | null
  rehearsal_count?: number | null
  readiness_score?: number | null
}

export interface PitchTaskCreate {
  name: string
  customer_name?: string
  customer_industry?: string
  budget?: number
  bid_date?: string
  bid_time_limit?: number
  bid_requirements?: string
  competitor_info?: Array<{ name: string; strengths?: string; weaknesses?: string }>
}

export const pitchTaskApi = {
  list: () => api.get<PitchTask[]>('/pitch-tasks'),
  get: (id: number) => api.get<PitchTask>(`/pitch-tasks/${id}`),
  create: (data: PitchTaskCreate) => api.post<PitchTask>('/pitch-tasks', data),
  update: (id: number, data: Partial<PitchTaskCreate>) => api.patch<PitchTask>(`/pitch-tasks/${id}`, data),
  archive: (id: number) => api.delete(`/pitch-tasks/${id}`),
}
