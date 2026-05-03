import { api } from './index'

export interface EvaluatorPersona {
  id: string | number
  name: string
  role: string
  description: string | null
  avatar_emoji: string | null
  difficulty: number
  focus_areas: string[] | null
  persona_type: string
}

export interface QAMessage {
  role: 'evaluator' | 'user'
  content: string
  answered?: boolean
  audio_url?: string
  score?: number
}

export interface QASession {
  id: number
  evaluator_id: number | null
  preset_persona_id: string | null
  session_type: string
  messages: QAMessage[]
  status: number // 0=init 1=in_progress 2=completed
  total_score: number | null
  feedback: string | null
  created_at: string
}

export const evaluatorsApi = {
  listPresets: () => api.get<EvaluatorPersona[]>('/evaluators/presets'),
  list: () => api.get<EvaluatorPersona[]>('/evaluators'),

  startSession: (taskId: number, data: { preset_persona_id?: string; evaluator_id?: number; session_type?: string }) =>
    api.post<QASession>(`/evaluators/sessions/${taskId}`, data),
  submitAnswer: (sessionId: number, answer: string) =>
    api.post<QASession>(`/evaluators/sessions/${sessionId}/answer`, { answer }),
  completeSession: (sessionId: number) =>
    api.post<QASession>(`/evaluators/sessions/${sessionId}/complete`),
  listSessions: (taskId?: number) =>
    api.get<QASession[]>('/evaluators/sessions', { params: taskId ? { task_id: taskId } : {} }),
  getSession: (sessionId: number) =>
    api.get<QASession>(`/evaluators/sessions/${sessionId}`),
}
