import axios from 'axios'
import { useUpgradeBanner } from '@/composables/useUpgradeBanner'

export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

// Attach JWT — reads from localStorage so it works even before Pinia hydrates
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Redirect to login on 401; show upgrade banner on 402
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err.response?.status
    if (status === 401) {
      localStorage.removeItem('access_token')
      const router = (window as any).__vue_router__
      if (router) router.push('/login')
      else window.location.href = '/login'
    } else if (status === 402) {
      const data = err.response?.data ?? {}
      const { show } = useUpgradeBanner()
      show({
        feature:    data.feature    ?? 'unknown',
        used:       data.used       ?? 0,
        limit:      data.limit      ?? 0,
        label:      data.label,
        message:    data.message,
        trigger_id: data.trigger_id,
      })
    }
    return Promise.reject(err)
  },
)
