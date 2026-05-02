import { api } from './index'

export interface RegisterPayload { company_name: string; name: string; email: string; password: string }
export interface LoginPayload { email: string; password: string }
export interface TokenResponse { access_token: string; user_id: number; name: string; tenant_id: number; role: string }
export interface UserProfile { id: number; name: string; email: string; role: string; tenant_id: number; avatar_url: string | null }

export const authApi = {
  register: (data: RegisterPayload) => api.post<TokenResponse>('/auth/register', data),
  login: (data: LoginPayload) => api.post<TokenResponse>('/auth/login', data),
  me: () => api.get<UserProfile>('/auth/me'),
}
