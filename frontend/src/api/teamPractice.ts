import { api } from './index'

export interface TeamRole {
  role: string
  description: string
  suggested_duration_sec: number
}

export interface TeamParticipant {
  id: number
  session_id: number
  user_id: number
  role_index: number
  role_name: string
  rehearsal_id: number | null
  status: number  // 0=joined, 1=submitted
  score: number | null
  feedback: string | null
  joined_at: string
  submitted_at: string | null
}

export interface TeamSession {
  id: number
  pitch_task_id: number
  created_by: number
  title: string
  description: string | null
  roles: TeamRole[]
  status: number  // 0=draft, 1=open, 2=in_progress, 3=completed
  avg_score: number | null
  total_score: number | null
  feedback: string[] | null
  created_at: string
  participants?: TeamParticipant[]
}

export const teamPracticeApi = {
  createSession: (data: {
    pitch_task_id: number
    title: string
    description?: string
    roles: TeamRole[]
  }) => api.post<TeamSession>('/team-practice/sessions', data),

  listSessions: (pitch_task_id?: number) =>
    api.get<TeamSession[]>('/team-practice/sessions', { params: pitch_task_id ? { pitch_task_id } : {} }),

  getSession: (id: number) =>
    api.get<TeamSession>(`/team-practice/sessions/${id}`),

  join: (sessionId: number, role_index: number) =>
    api.post<TeamParticipant>(`/team-practice/sessions/${sessionId}/join`, { role_index }),

  submit: (sessionId: number, rehearsal_id: number) =>
    api.post<TeamParticipant>(`/team-practice/sessions/${sessionId}/submit`, { rehearsal_id }),

  complete: (sessionId: number) =>
    api.post<TeamSession>(`/team-practice/sessions/${sessionId}/complete`),
}
