import { api } from './index'

export interface ScenarioSummary {
  id: string
  industry: string
  name: string
  customer_type: string
  difficulty: number
  difficulty_label: string
  duration_min: number
  description: string
  tags: string[]
  evaluator_types: string[]
}

export interface ScenarioDetail extends ScenarioSummary {
  background: string
  key_challenges: string[]
  checklist: string[]
  common_questions: string[]
}

export interface Industry {
  id: string
  name: string
  scenario_count: number
}

export interface ScenarioStartResult {
  session_id: number
  scenario: ScenarioSummary
  persona: {
    id: string
    name: string
    role: string
    description: string
    avatar_emoji: string
    difficulty: number
    focus_areas: string[]
  }
  difficulty: number
  difficulty_label: string
  opening_questions: string[]
  checklist: string[]
  duration_min: number
  message: string
}

export interface AdaptiveDifficulty {
  current_difficulty: number
  current_label: string
  recommended_difficulty: number
  recommended_label: string
  reason: string
  recent_scores: number[]
}

export const scenariosApi = {
  list: (params?: { industry?: string; difficulty?: number; search?: string }) =>
    api.get<ScenarioSummary[]>('/scenarios', { params }),

  industries: () => api.get<Industry[]>('/scenarios/industries'),

  get: (scenarioId: string) => api.get<ScenarioDetail>(`/scenarios/${scenarioId}`),

  start: (scenarioId: string, body: {
    task_id?: number
    persona_id: string
    difficulty?: number
    pitch_summary?: string
  }) => api.post<ScenarioStartResult>(`/scenarios/${scenarioId}/start`, body),

  adaptiveDifficulty: (body: { current_difficulty: number; recent_scores?: number[] }) =>
    api.post<AdaptiveDifficulty>('/scenarios/adaptive-difficulty', body),

  recommend: (taskId: number) =>
    api.get<{ task_name: string; customer_industry: string; recommended: ScenarioSummary[] }>(
      `/scenarios/recommend/${taskId}`
    ),
}
