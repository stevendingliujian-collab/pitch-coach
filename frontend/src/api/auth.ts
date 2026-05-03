import { api } from './index'

// ── Types ──────────────────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string
  token_type: string
  user_id: number
  name: string
  tenant_id: number
  role: string
  is_new_user: boolean
  profile_completeness: number
}

export interface UserProfile {
  id: number
  name: string | null
  email: string | null
  phone: string | null
  role: string
  tenant_id: number
  avatar_url: string | null
  industry: string | null
  profile_completeness: number
  register_source: string
  created_at: string | null
}

export interface WechatQrcodeResponse {
  qrcode_url: string
  session_key: string
  expires_in: number
}

export interface WechatQrcodeStatusResponse {
  status: 'pending' | 'scanned' | 'confirmed' | 'expired'
  token_response: TokenResponse | null
}

export interface ProfileUpdatePayload {
  name?: string
  industry?: string
  role?: string
}

// Backward-compat
export type RegisterPayload = { company_name?: string; name?: string; email: string; password: string }
export type LoginPayload = { email: string; password: string }

// ── API ─────────────────────────────────────────────────────────────────────

export const authApi = {
  // SMS
  smsSend: (phone: string) =>
    api.post<{ message: string; ttl: number }>('/auth/sms/send', { phone }),

  smsLogin: (phone: string, code: string, channel?: string) =>
    api.post<TokenResponse>('/auth/sms/login', { phone, code, channel }),

  // WeChat QR
  wechatQrcode: () =>
    api.post<WechatQrcodeResponse>('/auth/wechat/qrcode'),

  wechatQrcodeStatus: (sessionKey: string) =>
    api.get<WechatQrcodeStatusResponse>(`/auth/wechat/qrcode/status?session_key=${sessionKey}`),

  // Email
  register: (data: RegisterPayload) =>
    api.post<TokenResponse>('/auth/register', data),

  login: (data: LoginPayload) =>
    api.post<TokenResponse>('/auth/login', data),

  // Profile
  me: () => api.get<UserProfile>('/auth/me'),

  updateProfile: (data: ProfileUpdatePayload) =>
    api.put<UserProfile>('/auth/profile', data),
}
