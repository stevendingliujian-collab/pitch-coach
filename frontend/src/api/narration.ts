import { api } from './index'

export interface PageAudio {
  page_number: number
  script: string
  tone: string
  audio_url: string
  duration_sec: number
}

export interface VoicePreset {
  id: string
  name: string
}

export interface DemoNarration {
  id: number
  plan_id: number
  voice_id: string
  voice_name: string | null
  speed: number
  status: number
  status_label: string
  page_audios: PageAudio[] | null
  total_audio_url: string | null
  total_duration_sec: number | null
  error_msg: string | null
}

export const narrationApi = {
  generate: (planId: number, params: { voice_id: string; voice_name: string; speed: number }) =>
    api.post<{ narration_id: number; status: string }>(`/narrations/${planId}/generate`, params),

  getLatest: (planId: number) =>
    api.get<DemoNarration>(`/narrations/${planId}/latest`),

  list: (planId: number) =>
    api.get<DemoNarration[]>(`/narrations/${planId}/list`),

  listVoices: () =>
    api.get<VoicePreset[]>('/narrations/voices'),
}
