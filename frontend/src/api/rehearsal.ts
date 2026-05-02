import axios from 'axios'
import { api } from './index'

export interface PageTiming {
  page_number: number
  start_sec: number
  end_sec: number
}

export interface FillerWordDetail {
  word: string
  count: number
  positions: number[]
}

export interface PageScore {
  page_number: number
  actual_duration_sec: number
  suggested_duration_sec: number
  timing_ok: boolean
  importance_level: number
}

export interface RehearsalStatus {
  rehearsal_id: number
  status: number
  total_score: number | null
  fluency_score: number | null
  rate_score: number | null
  timing_score: number | null
}

export interface RehearsalReport extends RehearsalStatus {
  pitch_task_id: number
  audio_url: string
  audio_duration: number
  filler_count: number | null
  filler_detail: FillerWordDetail[]
  chars_per_min: number | null
  total_duration_sec: number | null
  improvement_tips: string[]
  page_scores: PageScore[]
  page_timings: PageTiming[]
  created_at: string
}

export interface RehearsalListItem {
  rehearsal_id: number
  pitch_task_id: number
  status: number
  total_score: number | null
  audio_duration: number
  created_at: string
}

export const rehearsalApi = {
  start: (pitchTaskId: number, planId: number | null) =>
    api.post<{ rehearsal_id: number; upload_url: string; object_key: string }>(
      '/rehearsals/start',
      { pitch_task_id: pitchTaskId, plan_id: planId }
    ),

  uploadAudio: (uploadUrl: string, blob: Blob, onProgress?: (pct: number) => void) =>
    axios.put(uploadUrl, blob, {
      headers: { 'Content-Type': 'audio/webm' },
      onUploadProgress: (e) => {
        if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100))
      },
    }),

  complete: (rehearsalId: number, data: { object_key: string; audio_duration: number; page_timings: PageTiming[] }) =>
    api.post<RehearsalStatus>(`/rehearsals/${rehearsalId}/complete`, data),

  getStatus: (rehearsalId: number) =>
    api.get<RehearsalStatus>(`/rehearsals/${rehearsalId}/status`),

  getReport: (rehearsalId: number) =>
    api.get<RehearsalReport>(`/rehearsals/${rehearsalId}/report`),

  listByTask: (pitchTaskId: number) =>
    api.get<RehearsalListItem[]>(`/rehearsals/task/${pitchTaskId}`),
}
