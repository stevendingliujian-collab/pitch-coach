import { api } from './index'

// ─── API Key types ────────────────────────────────────────────────────────────

export interface ApiKeySummary {
  id: number
  name: string
  key_prefix: string
  scopes: string[]
  is_active: boolean
  last_used_at: string | null
  expires_at: string | null
  created_at: string
  usage_count: number
}

export interface ApiKeyCreated extends ApiKeySummary {
  key: string   // Full key — shown ONCE only
  warning: string
}

export interface CreateApiKeyBody {
  name: string
  scopes?: string[]
  expires_days?: number | null
}

export interface UpdateApiKeyBody {
  name?: string
  scopes?: string[]
}

// ─── Usage types ──────────────────────────────────────────────────────────────

export interface ApiUsageStats {
  period_days: number
  total_calls: number
  error_count: number
  error_rate: number
  by_endpoint: { endpoint: string; count: number }[]
  by_key: { api_key_id: number; count: number }[]
}

// ─── Webhook types ────────────────────────────────────────────────────────────

export interface WebhookSummary {
  id: number
  url: string
  events: string[]
  is_active: boolean
  created_at: string
}

export interface WebhookCreated extends WebhookSummary {
  signing_secret: string  // shown ONCE
  warning: string
}

export interface CreateWebhookBody {
  url: string
  events?: string[]
  secret?: string
}

export interface WebhookTestResult {
  success: boolean
  status_code?: number
  url: string
  message: string
  error?: string
}

export interface AvailableEvent {
  event: string
  description: string
}

// ─── API ─────────────────────────────────────────────────────────────────────

export const openApiApi = {
  // API Keys
  createKey: (body: CreateApiKeyBody) =>
    api.post<ApiKeyCreated>('/open-api/keys', body),

  listKeys: () =>
    api.get<ApiKeySummary[]>('/open-api/keys'),

  revokeKey: (keyId: number) =>
    api.delete(`/open-api/keys/${keyId}`),

  updateKey: (keyId: number, body: UpdateApiKeyBody) =>
    api.patch<ApiKeySummary>(`/open-api/keys/${keyId}`, body),

  // Usage stats
  getUsage: (days = 30) =>
    api.get<ApiUsageStats>('/open-api/usage', { params: { days } }),

  // Webhooks
  listWebhooks: () =>
    api.get<WebhookSummary[]>('/open-api/webhooks'),

  createWebhook: (body: CreateWebhookBody) =>
    api.post<WebhookCreated>('/open-api/webhooks', body),

  deleteWebhook: (webhookId: number) =>
    api.delete(`/open-api/webhooks/${webhookId}`),

  testWebhook: (webhookId: number) =>
    api.post<WebhookTestResult>(`/open-api/webhooks/${webhookId}/test`),

  availableEvents: () =>
    api.get<AvailableEvent[]>('/open-api/available-events'),
}
