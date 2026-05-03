import { api } from './index'

export interface Notification {
  type: string
  level: 'urgent' | 'warning' | 'info' | 'success'
  title: string
  message: string
  task_id?: number
  task_name?: string
  rehearsal_id?: number
  bid_date?: string
  action_url?: string
}

export const notificationsApi = {
  list: () => api.get<Notification[]>('/notifications'),
}
