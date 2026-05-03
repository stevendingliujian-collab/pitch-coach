import { api } from './index'

export interface TeamMember {
  id: number
  name: string
  email: string | null
  phone: string | null
  role: string
  avatar_url: string | null
  profile_completeness: number
  created_at: string | null
}

export interface TeamInvite {
  id: number
  invite_code: string
  grant_role: string
  note: string | null
  max_uses: number
  used_count: number
  is_valid: boolean
  expires_at: string | null
  created_at: string
}

export interface InvitePreview {
  invite_code: string
  company_name: string
  grant_role: string
  note: string | null
  is_valid: boolean
}

export const teamApi = {
  listMembers: () => api.get<TeamMember[]>('/team/members'),

  listInvites: () => api.get<TeamInvite[]>('/team/invites'),

  createInvite: (data: { max_uses?: number; grant_role?: string; note?: string; expire_days?: number }) =>
    api.post<TeamInvite>('/team/invites', data),

  revokeInvite: (id: number) => api.delete(`/team/invites/${id}`),

  previewInvite: (code: string) => api.get<InvitePreview>(`/team/invites/${code}/preview`),

  joinTeam: (invite_code: string) => api.post('/team/join', { invite_code }),
}
