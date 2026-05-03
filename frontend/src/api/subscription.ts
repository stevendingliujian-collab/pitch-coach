import { api } from './index'

export interface SubscriptionStatus {
  id: number
  tenant_id: number
  status: 'free' | 'trial' | 'active' | 'cancelled' | 'expired'
  plan_type: string
  is_active: boolean
  effective_plan: 'free' | 'pro'
  trial_days_left: number | null
  trial_starts_at: string | null
  trial_ends_at: string | null
  expires_at: string | null
  created_at: string
}

export const subscriptionApi = {
  get: () => api.get<SubscriptionStatus>('/subscription'),
  getStatus: () => api.get<{ plan: string; status: string; trial_days_left: number | null; is_active: boolean }>('/subscription/status'),
  startTrial: () => api.post<SubscriptionStatus>('/subscription/trial/start'),
}
