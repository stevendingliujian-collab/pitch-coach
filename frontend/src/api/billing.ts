import { api } from './index'

export interface PlanInfo {
  id: string
  name: string
  monthly_price: number
  annual_price: number
  max_users: number
  features: string[]
}

export interface PaymentRecord {
  id: number
  plan_type: string
  billing_cycle: string
  amount: number
  currency: string
  status: string
  payment_method: string
  description: string | null
  invoice_no: string | null
  period_start: string | null
  period_end: string | null
  created_at: string
}

export interface BillingOverview {
  subscription: {
    status: string
    plan_type: string
    is_active: boolean
    effective_plan: string
    trial_days_left: number | null
    trial_ends_at: string | null
    expires_at: string | null
    cancelled_at: string | null
  }
  plan_info: {
    id: string
    name: string
    monthly_price: number
    annual_price: number
    max_users: number
  }
  usage: {
    year_month: string
    ppt_uploads: number
    rehearsals: number
    narration_pages: number
    knowledge_docs: number
    limits: {
      ppt_uploads: number | null
      rehearsals: number | null
      narration_pages: number | null
      knowledge_docs: number | null
    }
  }
  upcoming_renewal: {
    date: string
    amount: number
    plan_name: string
    billing_cycle: string
  } | null
}

export const billingApi = {
  listPlans: () => api.get<Record<string, PlanInfo>>('/billing/plans'),
  getOverview: () => api.get<BillingOverview>('/billing/overview'),
  upgrade: (data: { plan_type: string; billing_cycle?: string; payment_method?: string }) =>
    api.post('/billing/upgrade', data),
  cancel: () => api.post('/billing/cancel'),
  listPayments: () => api.get<PaymentRecord[]>('/billing/payments'),
  getInvoice: (invoiceNo: string) => api.get(`/billing/invoice/${invoiceNo}`),
}
