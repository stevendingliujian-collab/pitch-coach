import axios from 'axios'
import { api } from './index'

export interface UpcomingTask {
  task_id: number
  name: string
  bid_date: string
  days_left: number
}

export interface TodayPractice {
  item_id: number
  practice_type: string
  title: string
  instruction: string
  target_duration_sec: number
  key_points: string[]
  log_id: number | null
  status: number          // 0=未开始 1=已完成
  current_streak: number
  last_practice_date: string | null
  upcoming_task: UpcomingTask | null
}

export interface StartPracticeResponse {
  log_id: number
  upload_url: string
  object_key: string
}

export interface PracticeScoreResponse {
  log_id: number
  total_score: number
  completion_ok: boolean
  timing_sec: number
  filler_count: number
  keyword_hit_rate: number
  feedback: string[]
  reference_answer: string | null
  current_streak: number
  longest_streak: number
  is_new_record: boolean
}

export interface PracticeHistoryItem {
  log_id: number
  practice_date: string
  title: string
  practice_type: string
  total_score: number | null
  status: number
  audio_duration_sec: number | null
}

export interface StreakInfo {
  current_streak: number
  longest_streak: number
  total_practices: number
  last_practice_date: string | null
}

export const dailyPracticeApi = {
  getToday: () =>
    api.get<TodayPractice>('/daily-practice/today'),

  start: (itemId: number) =>
    api.post<StartPracticeResponse>('/daily-practice/start', null, {
      params: { item_id: itemId },
    }),

  uploadAudio: (uploadUrl: string, blob: Blob, onProgress?: (pct: number) => void) =>
    axios.put(uploadUrl, blob, {
      headers: { 'Content-Type': 'audio/webm' },
      onUploadProgress: (e) => {
        if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100))
      },
    }),

  complete: (data: {
    log_id: number
    object_key: string
    audio_duration_sec: number
    transcript?: string
  }) =>
    api.post<PracticeScoreResponse>('/daily-practice/complete', data),

  getHistory: (limit = 14) =>
    api.get<PracticeHistoryItem[]>('/daily-practice/history', { params: { limit } }),

  getStreak: () =>
    api.get<StreakInfo>('/daily-practice/streak'),
}
