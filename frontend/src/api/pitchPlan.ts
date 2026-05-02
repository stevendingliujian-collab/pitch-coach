import { api } from './index'
import axios from 'axios'

export interface TalkingPoint { point: string; is_emphasis: boolean }
export interface PlanPage {
  id: number; page_number: number; page_title: string | null
  page_content_summary: string | null; page_thumbnail_url: string | null
  importance_level: number; talking_points: TalkingPoint[]
  suggested_duration: number; emphasis_marks: any[] | null
  bid_req_mapping: any[] | null; transition_hint: string | null
  opening_templates: any[] | null; closing_templates: any[] | null
  is_manually_edited: boolean
}

export interface PitchPlan {
  id: number; pitch_task_id: number; ppt_file_id: string; ppt_file_name: string
  ppt_page_count: number; global_strategy: string | null; total_duration_sec: number | null
  predicted_questions: any[] | null; competitive_differentiation: any[] | null
  opening_templates: any[] | null; closing_templates: any[] | null
  status: number; version: number; pages: PlanPage[]
}

export const pitchPlanApi = {
  getUploadUrl: (filename: string) =>
    api.post<{ upload_url: string; object_key: string }>('/pitch-plans/upload-url', null, { params: { filename } }),

  uploadToMinio: (uploadUrl: string, file: File, onProgress?: (pct: number) => void) =>
    axios.put(uploadUrl, file, {
      headers: { 'Content-Type': file.type || 'application/octet-stream' },
      onUploadProgress: (e) => { if (onProgress && e.total) onProgress(Math.round(e.loaded / e.total * 100)) },
    }),

  generate: (data: { pitch_task_id: number; ppt_file_id: string; ppt_file_name: string; bid_requirements?: string; bid_time_limit?: number }) =>
    api.post<{ plan_id: number; status: string; estimated_seconds: number }>('/pitch-plans/generate', data),

  get: (planId: number) => api.get<PitchPlan>(`/pitch-plans/${planId}`),

  listByTask: (taskId: number) => api.get<PitchPlan[]>(`/pitch-plans/by-task/${taskId}`),

  updatePage: (planId: number, pageNumber: number, data: Partial<PlanPage>) =>
    api.put<PlanPage>(`/pitch-plans/${planId}/pages/${pageNumber}`, data),

  regenerate: (planId: number, data?: { scope?: string; page_number?: number; user_instruction?: string }) =>
    api.post(`/pitch-plans/${planId}/regenerate`, data ?? {}),
}
