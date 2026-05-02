import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, type UserProfile } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const user = ref<UserProfile | null>(null)

  const isLoggedIn = computed(() => !!token.value)
  const tenantId = computed(() => user.value?.tenant_id ?? 0)

  function setToken(t: string) {
    token.value = t
    localStorage.setItem('access_token', t)
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('access_token')
  }

  async function fetchMe() {
    if (!token.value) return
    try {
      const res = await authApi.me()
      user.value = res.data
    } catch {
      logout()
    }
  }

  return { token, user, isLoggedIn, tenantId, setToken, logout, fetchMe }
})
