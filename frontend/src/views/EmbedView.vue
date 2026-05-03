<template>
  <div class="embed-shell">
    <!-- Loading -->
    <div v-if="embedState === 'loading'" class="embed-center">
      <div class="embed-spinner"></div>
      <p>正在连接 CRM…</p>
    </div>

    <!-- Error -->
    <div v-else-if="embedState === 'error'" class="embed-center">
      <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#EF4444" stroke-width="1.5">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="13"/>
        <circle cx="12" cy="17" r="0.5" fill="#EF4444"/>
      </svg>
      <p class="embed-err-msg">{{ errorMsg }}</p>
      <button class="embed-btn embed-btn-primary" @click="init">重试</button>
    </div>

    <!-- Ready -->
    <div v-else-if="embedState === 'ready'" class="embed-layout">
      <!-- Header -->
      <div class="embed-header">
        <div class="embed-brand">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366F1" stroke-width="2.2">
            <circle cx="12" cy="12" r="9"/><path d="M9 12l2 2 4-4"/>
          </svg>
          <span>AI 述标教练</span>
        </div>

        <div v-if="task" class="embed-task-badge">{{ task.name }}</div>

        <div class="embed-tabs" v-if="task">
          <button
            v-for="t in TABS"
            :key="t.id"
            :class="['embed-tab', { active: activeTab === t.id }]"
            @click="activeTab = t.id"
          >{{ t.label }}</button>
        </div>
      </div>

      <!-- Body -->
      <div class="embed-body">
        <!-- No task linked -->
        <div v-if="!task" class="embed-no-task">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#CBD5E1" stroke-width="1.5">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/><line x1="12" y1="11" x2="12" y2="17"/>
            <line x1="9" y1="14" x2="15" y2="14"/>
          </svg>
          <p>当前商机未关联述标任务</p>
          <button
            class="embed-btn embed-btn-primary"
            :disabled="creating"
            @click="createTask"
          >
            {{ creating ? '创建中…' : '为此商机创建述标任务' }}
          </button>
        </div>

        <template v-else>
          <PlanTab
            v-if="activeTab === 'plan'"
            :task="task"
            :plan="currentPlan"
            @plan-created="(p: any) => currentPlan = p"
          />
          <RehearsalTab
            v-else-if="activeTab === 'rehearsal'"
            :task-id="task.id"
            :plan-id="currentPlan?.id ?? null"
          />
          <ReadinessTab
            v-else-if="activeTab === 'readiness'"
            :task-id="task.id"
            :task="task"
          />
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api/auth'
import { pitchTaskApi, type PitchTask } from '@/api/pitchTask'
import { pitchPlanApi, type PitchPlan } from '@/api/pitchPlan'
import PlanTab from '@/components/PlanTab.vue'
import RehearsalTab from '@/components/RehearsalTab.vue'
import ReadinessTab from '@/components/ReadinessTab.vue'

const TABS = [
  { id: 'plan', label: '讲解方案' },
  { id: 'rehearsal', label: '对练排练' },
  { id: 'readiness', label: '就绪清单' },
]

const route = useRoute()
const auth = useAuthStore()

type EmbedState = 'loading' | 'ready' | 'error'
const embedState = ref<EmbedState>('loading')
const errorMsg = ref('')
const task = ref<PitchTask | null>(null)
const currentPlan = ref<PitchPlan | null>(null)
const activeTab = ref('plan')
const creating = ref(false)

async function init() {
  embedState.value = 'loading'
  errorMsg.value = ''

  const ssoToken = route.query.token as string | undefined
  const taskId = route.query.task_id ? Number(route.query.task_id) : null

  // 1. Authenticate via SSO or existing token
  if (ssoToken) {
    try {
      const res = await authApi.ssoLogin(ssoToken)
      auth.setToken(res.data.access_token)
    } catch (e: any) {
      embedState.value = 'error'
      errorMsg.value = `SSO 认证失败：${e?.response?.data?.detail ?? '请从 CRM 重新打开'}`
      return
    }
  } else if (!auth.token) {
    embedState.value = 'error'
    errorMsg.value = '未提供认证 Token，请从 CRM 系统打开此页面'
    return
  }

  // 2. Load task if task_id provided
  if (taskId) {
    try {
      const res = await pitchTaskApi.get(taskId)
      task.value = res.data
      try {
        const planRes = await pitchPlanApi.listByTask(taskId)
        if (planRes.data.length > 0) currentPlan.value = planRes.data[0]
      } catch { /* no plan yet */ }
    } catch {
      // Task not found — user can create one
    }
  }

  // 3. Tell CRM parent we are ready
  window.parent?.postMessage(
    { type: 'PITCH_COACH_READY', taskId: task.value?.id ?? null },
    '*'
  )

  embedState.value = 'ready'
}

async function createTask() {
  creating.value = true
  const name = (route.query.opportunity_name as string | undefined) || '来自 CRM 的商机'
  try {
    const res = await pitchTaskApi.create({ name })
    task.value = res.data
    window.parent?.postMessage(
      { type: 'PITCH_COACH_TASK_CREATED', taskId: task.value.id },
      '*'
    )
  } catch (e: any) {
    errorMsg.value = `创建失败：${e?.response?.data?.detail ?? '请稍后重试'}`
  } finally {
    creating.value = false
  }
}

// Handle navigation commands from CRM parent frame
function handleMessage(event: MessageEvent) {
  if (event.data?.type === 'PITCH_COACH_NAVIGATE') {
    const tab = TABS.find(t => t.id === event.data.tab)
    if (tab) activeTab.value = tab.id
  }
}

onMounted(() => {
  init()
  window.addEventListener('message', handleMessage)
})
onUnmounted(() => window.removeEventListener('message', handleMessage))
</script>

<style scoped>
.embed-shell {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #F5F5F7;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* Center states */
.embed-center {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  color: #64748B;
  font-size: 14px;
}

.embed-spinner {
  width: 30px;
  height: 30px;
  border: 3px solid #E2E8F0;
  border-top-color: #6366F1;
  border-radius: 50%;
  animation: spin 0.75s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.embed-err-msg {
  color: #EF4444;
  text-align: center;
  max-width: 280px;
}

/* Layout */
.embed-layout {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.embed-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  background: #fff;
  border-bottom: 1px solid #E2E8F0;
  flex-shrink: 0;
  flex-wrap: wrap;
}

.embed-brand {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  font-weight: 700;
  color: #1E293B;
  white-space: nowrap;
}

.embed-task-badge {
  font-size: 12px;
  color: #64748B;
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}

.embed-tabs {
  display: flex;
  gap: 4px;
  margin-left: auto;
  flex-shrink: 0;
}

.embed-tab {
  font-size: 12px;
  padding: 3px 10px;
  border: 1px solid #E2E8F0;
  border-radius: 6px;
  background: transparent;
  color: #64748B;
  cursor: pointer;
  transition: all 0.15s;
}

.embed-tab.active {
  background: #6366F1;
  color: #fff;
  border-color: #6366F1;
}

.embed-tab:hover:not(.active) { background: #F1F5F9; }

/* Body */
.embed-body {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
}

.embed-no-task {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  height: 200px;
  color: #94A3B8;
  font-size: 14px;
}

/* Button */
.embed-btn {
  border: none;
  border-radius: 8px;
  padding: 8px 20px;
  font-size: 13px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.embed-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.embed-btn-primary {
  background: #6366F1;
  color: #fff;
}

.embed-btn-primary:hover:not(:disabled) { background: #4F46E5; }
</style>
