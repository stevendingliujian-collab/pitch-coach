import { api } from './index'

export interface GoldenScript {
  id: number
  rehearsal_id: number | null
  page_number: number
  start_sec: number | null
  end_sec: number | null
  transcript: string
  audio_clip_url: string | null
  tags: string[]
  marked_by: number
  usage_count: number
  created_at: string | null
}

export interface GoldenScriptList {
  total: number
  page: number
  page_size: number
  items: GoldenScript[]
}

export interface MarkGoldenScriptBody {
  rehearsal_id: number
  page_number: number
  start_sec?: number
  end_sec?: number
  transcript: string
  tags?: string[]
  audio_clip_url?: string
}

export const goldenScriptsApi = {
  mark: (body: MarkGoldenScriptBody) =>
    api.post<GoldenScript>('/golden-scripts', body),

  list: (params?: { rehearsal_id?: number; page?: number; page_size?: number }) =>
    api.get<GoldenScriptList>('/golden-scripts', { params }),

  get: (id: number) =>
    api.get<GoldenScript>(`/golden-scripts/${id}`),

  delete: (id: number) =>
    api.delete(`/golden-scripts/${id}`),

  extractFromQA: (qaSessionId: number, taskName = '') =>
    api.post('/golden-scripts/from-qa', { qa_session_id: qaSessionId, task_name: taskName }),
}
