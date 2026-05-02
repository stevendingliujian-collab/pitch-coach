<template>
  <div>
    <el-empty v-if="!ready" description="正在连接 CRM…" />
    <PlanTab v-else-if="task && activeTab === 'plan'" :task="task" :plan="currentPlan" @plan-created="(p) => currentPlan = p" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api/auth'
import { pitchTaskApi, type PitchTask } from '@/api/pitchTask'
import { pitchPlanApi, type PitchPlan } from '@/api/pitchPlan'
import PlanTab from '@/components/PlanTab.vue'

const route = useRoute()
const auth = useAuthStore()
const ready = ref(false)
const task = ref<PitchTask | null>(null)
const currentPlan = ref<PitchPlan | null>(null)
const activeTab = ref('plan')

onMounted(async () => {
  const token = route.query.token as string
  const opportunityId = route.query.opportunity_id as string
  if (!token) return

  // Exchange SSO token
  try {
    const res = await authApi.login({ email: '', password: '' }) // replaced by SSO exchange in Phase 3
    auth.setToken(res.data.access_token)
  } catch { /* SSO stub */ }

  ready.value = true
})
</script>
