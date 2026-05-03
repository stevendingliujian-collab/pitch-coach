import { api } from './index'

export interface RubricItem {
  id: string
  category: string
  item: string
  max_score: number
  weight: number
  description: string
}

export interface ScoringRubric {
  id: number
  name: string
  description: string | null
  source_type: string
  items: RubricItem[]
  total_max_score: number | null
  industry: string | null
  template_type: string | null
  is_template: boolean
  created_at: string
}

export interface RubricScoreItem {
  item_id: string
  score: number
  coverage: boolean
  note: string
  suggest_page: number | null
}

export interface RubricScore {
  id: number
  rubric_id: number
  rehearsal_id: number
  scores: RubricScoreItem[]
  total_score: number | null
  coverage_percent: number | null
  coverage_detail: Array<{ item_id: string; covered: boolean; evidence: string }> | null
  improvement_suggestions: Array<{ item_id: string; suggestion: string }> | null
  created_at: string
}

export interface PresetTemplate {
  template_type: string
  name: string
  industry: string
  description: string
  items: RubricItem[]
  total_max_score: number
}

export const rubricsApi = {
  listTemplates: () => api.get<PresetTemplate[]>('/rubrics/templates'),
  importTemplate: (templateType: string) =>
    api.post<ScoringRubric>(`/rubrics/templates/${templateType}/import`),

  list: () => api.get<ScoringRubric[]>('/rubrics'),
  create: (data: { name: string; description?: string; items: Partial<RubricItem>[]; industry?: string }) =>
    api.post<ScoringRubric>('/rubrics', data),
  get: (id: number) => api.get<ScoringRubric>(`/rubrics/${id}`),
  update: (id: number, data: Partial<{ name: string; description: string; items: Partial<RubricItem>[]; industry: string }>) =>
    api.patch<ScoringRubric>(`/rubrics/${id}`, data),
  delete: (id: number) => api.delete(`/rubrics/${id}`),

  scoreCoverage: (rubricId: number, rehearsalId: number) =>
    api.post<RubricScore>(`/rubrics/${rubricId}/coverage/${rehearsalId}`),
  getCoverage: (rubricId: number, rehearsalId: number) =>
    api.get<RubricScore>(`/rubrics/${rubricId}/coverage/${rehearsalId}`),
}
