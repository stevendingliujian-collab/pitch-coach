import { api } from './index'

export interface DashboardOverview {
  total_tasks: number
  total_rehearsals: number
  month_rehearsals: number
  avg_score: number | null
  best_score: number | null
  upcoming_bids_7d: number
  year_month: string
}

export interface TrendPoint {
  date: string
  rehearsals: number
  avg_score: number | null
}

export interface MemberStat {
  rank: number
  user_id: number
  name: string
  rehearsal_count: number
  avg_score: number | null
  best_score: number | null
  last_rehearsed: string | null
}

export interface TaskReadiness {
  task_id: number
  name: string
  customer_name: string | null
  bid_date: string | null
  days_until_bid: number | null
  rehearsal_count: number
  avg_score: number | null
  best_score: number | null
  readiness_score: number
  last_rehearsed: string | null
}

export interface DashboardROI {
  total_practice_min: number
  total_rehearsals: number
  score_improvement: number | null
  first_avg_score: number | null
  recent_avg_score: number | null
  win_rate: number | null
  won_count: number
  total_outcomes: number
  won_budget_total: number  // 万元
}

export interface BenchmarkMetric {
  key: string
  label: string
  unit: string
  my_value: number | null
  target: number
  pct_of_target: number | null
  higher_is_better: boolean
}

export interface DashboardBenchmark {
  metrics: BenchmarkMetric[]
  overall_pct: number | null
  period_days: number
  benchmark_label: string
}

export interface FunnelStage {
  key: string
  label: string
  count: number
  conversion_from_prev: number | null
  color: string
}

export interface DashboardFunnel {
  period_days: number
  stages: FunnelStage[]
  total_registered_alltime: number
}

export const dashboardApi = {
  getOverview: () => api.get<DashboardOverview>('/dashboard/overview'),
  getTrend: (days?: number) => api.get<{ days: number; points: TrendPoint[] }>('/dashboard/trend', { params: days ? { days } : {} }),
  getMembers: () => api.get<MemberStat[]>('/dashboard/members'),
  getTasks: () => api.get<TaskReadiness[]>('/dashboard/tasks'),
  getRoi: () => api.get<DashboardROI>('/dashboard/roi'),
  getBenchmark: () => api.get<DashboardBenchmark>('/dashboard/benchmark'),
  getFunnel: (days?: number) => api.get<DashboardFunnel>('/dashboard/funnel', { params: days ? { days } : {} }),
}
