import axios from 'axios'

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

// Redirect to login on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token')
      // Use Vue Router if available, otherwise hard redirect
      const router = (window as any).__vue_router__
      if (router) router.push('/login')
      else window.location.href = '/login'
    }
    return Promise.reject(err)
  },
)
