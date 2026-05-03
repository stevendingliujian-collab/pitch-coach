import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, type UserProfile, type TokenResponse } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const user = ref<UserProfile | null>(null)
  const loginSource = ref<string>('')
  const isNewUser = ref<boolean>(false)
  const profileCompleteness = ref<number>(0)

  const isLoggedIn = computed(() => !!token.value)
  const tenantId = computed(() => user.value?.tenant_id ?? 0)
  const displayName = computed(() => user.value?.name || '用户')

  function setToken(t: string) {
    token.value = t
    localStorage.setItem('access_token', t)
  }

  function applyTokenResponse(res: TokenResponse) {
    setToken(res.access_token)
    isNewUser.value = res.is_new_user
    profileCompleteness.value = res.profile_completeness
    loginSource.value = ''
  }

  function logout() {
    token.value = null
    user.value = null
    isNewUser.value = false
    profileCompleteness.value = 0
    loginSource.value = ''
    localStorage.removeItem('access_token')
  }

  async function fetchMe() {
    if (!token.value) return
    try {
      const res = await authApi.me()
      user.value = res.data
      profileCompleteness.value = res.data.profile_completeness
    } catch {
      logout()
    }
  }

  return {
    token,
    user,
    loginSource,
    isNewUser,
    profileCompleteness,
    isLoggedIn,
    tenantId,
    displayName,
    setToken,
    applyTokenResponse,
    logout,
    fetchMe,
  }
})
