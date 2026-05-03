<template>
  <div class="v2-page pd-page">
    <!-- Topbar -->
    <div class="v2-topbar pd-topbar">
      <button class="pd-back-btn" @click="router.push('/projects')">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="9 2 4 7 9 12"/>
        </svg>
        返回
      </button>
      <span class="pd-divider">/</span>
      <span class="pd-project-name">{{ task?.name ?? '加载中…' }}</span>
      <div class="v2-topbar-flex" />
      <button class="btn-v2 btn-v2-ghost" @click="exportPlan">
        <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M6.5 1v8M3 6l3.5 4 3.5-4"/><rect x="1" y="10" width="11" height="2" rx="1"/>
        </svg>
        导出方案
      </button>
      <button class="btn-v2 btn-v2-primary" @click="activeTab = 'rehearsal'">
        <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="6.5" cy="6.5" r="5"/><polygon points="5 4.5 9.5 6.5 5 8.5" fill="currentColor" stroke="none"/>
        </svg>
        开始排练
      </button>
    </div>

    <!-- Custom tab nav -->
    <div class="pd-tab-nav">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="pd-tab"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        <span class="pd-tab-icon" v-html="tab.icon" />
        {{ tab.label }}
      </button>
    </div>

    <!-- Content -->
    <div v-if="loading" class="v2-content">
      <el-skeleton :rows="8" animated />
    </div>
    <div v-else class="pd-tab-content">
      <PlanTab       v-if="activeTab === 'plan'"      :task="task!" :plan="currentPlan" @plan-created="onPlanCreated" />
      <NarrationTab  v-if="activeTab === 'narration'" :plan="currentPlan" :pages="currentPlan?.pages ?? []" />
      <RehearsalTab  v-if="activeTab === 'rehearsal'" :task-id="taskId" :plan-id="currentPlan?.id ?? null" />
      <TrainingTab   v-if="activeTab === 'training'"  :task-id="taskId" :plan-id="currentPlan?.id ?? null" :pages="currentPlan?.pages ?? []" />
      <ReviewTab     v-if="activeTab === 'review'"    :task-id="taskId" :plan-id="currentPlan?.id ?? null" />
      <RubricTab     v-if="activeTab === 'rubric'"    :task-id="taskId" :plan-id="currentPlan?.id ?? null" />
      <ReadinessTab    v-if="activeTab === 'readiness'"  :task-id="taskId" :task="task" @switch-tab="activeTab = $event" @task-updated="task = $event" />
      <TeamPracticeTab v-if="activeTab === 'team'"       :task-id="taskId" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { pitchTaskApi, type PitchTask } from '@/api/pitchTask'
import { pitchPlanApi, type PitchPlan } from '@/api/pitchPlan'
import PlanTab         from '@/components/PlanTab.vue'
import NarrationTab    from '@/components/NarrationTab.vue'
import RehearsalTab    from '@/components/RehearsalTab.vue'
import TrainingTab     from '@/components/TrainingTab.vue'
import ReviewTab       from '@/components/ReviewTab.vue'
import RubricTab       from '@/components/RubricTab.vue'
import ReadinessTab    from '@/components/ReadinessTab.vue'
import TeamPracticeTab from '@/components/TeamPracticeTab.vue'

const route   = useRoute()
const router  = useRouter()
const taskId  = Number(route.params.id)
const task    = ref<PitchTask | null>(null)
const currentPlan = ref<PitchPlan | null>(null)
const loading = ref(true)
const activeTab = ref('plan')

const tabs = [
  {
    key: 'plan',
    label: '讲解方案',
    icon: `<svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="2" y="1" width="10" height="12" rx="1.5"/><line x1="4" y1="5" x2="10" y2="5"/><line x1="4" y1="8" x2="8" y2="8"/></svg>`,
  },
  {
    key: 'rehearsal',
    label: '排练记录',
    icon: `<svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="7" cy="7" r="5.5"/><polygon points="5.5 4.5 10 7 5.5 9.5" fill="currentColor" stroke="none"/></svg>`,
  },
  {
    key: 'narration',
    label: 'AI 示范',
    icon: `<svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M2 4h10"/><path d="M2 7h7"/><path d="M2 10h5"/></svg>`,
  },
  {
    key: 'training',
    label: '跟读/背诵',
    icon: `<svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="2" y="3" width="4" height="6" rx="1"/><path d="M4 9v2M2 11h4"/><line x1="8" y1="5" x2="12" y2="5"/><line x1="8" y1="8" x2="11" y2="8"/></svg>`,
  },
  {
    key: 'review',
    label: '审核认证',
    icon: `<svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M7 1l1.5 4h4l-3 2.5 1.5 4L7 9 3 11.5l1.5-4L1.5 5h4z"/></svg>`,
  },
  {
    key: 'rubric',
    label: '评分对标',
    icon: `<svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="2" y="1" width="10" height="12" rx="1"/><line x1="4" y1="5" x2="10" y2="5"/><line x1="4" y1="8" x2="10" y2="8"/><polyline points="6 10 8 12 12 8"/></svg>`,
  },
  {
    key: 'readiness',
    label: '就绪清单',
    icon: `<svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="7" cy="7" r="5.5"/><polyline points="4 7 6 9.5 10.5 4.5"/></svg>`,
  },
  {
    key: 'team',
    label: '组队排练',
    icon: `<svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="5" cy="4.5" r="2"/><circle cx="9" cy="4.5" r="2"/><path d="M1 13c0-2.2 1.8-4 4-4"/><path d="M9 9c2.2 0 4 1.8 4 4"/></svg>`,
  },
]

onMounted(async () => {
  try {
    const [taskRes, plansRes] = await Promise.all([
      pitchTaskApi.get(taskId),
      pitchPlanApi.listByTask(taskId),
    ])
    task.value        = taskRes.data
    currentPlan.value = plansRes.data[0] ?? null
  } finally {
    loading.value = false
  }
})

function onPlanCreated(plan: PitchPlan) {
  currentPlan.value = plan
}

function exportPlan() {
  ElMessage.info('导出功能即将上线')
}
</script>

<style scoped>
.pd-page { background: var(--bg-content); }

/* Topbar extras */
.pd-topbar { gap: 8px; }
.pd-back-btn {
  display: flex; align-items: center; gap: 5px;
  background: none; border: none; font-size: 13px; font-weight: 500;
  color: var(--t-muted); cursor: pointer; padding: 4px 8px; border-radius: var(--radius-sm);
  transition: all 0.15s; font-family: inherit;
}
.pd-back-btn:hover { background: var(--bg-content); color: var(--t-primary); }
.pd-divider { color: var(--t-faint); font-size: 14px; }
.pd-project-name {
  font-size: 15px; font-weight: 700; color: var(--t-primary);
  max-width: 360px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

/* Tab nav */
.pd-tab-nav {
  display: flex; gap: 2px; padding: 0 20px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
  overflow-x: auto; scrollbar-width: none;
}
.pd-tab-nav::-webkit-scrollbar { display: none; }
.pd-tab {
  display: flex; align-items: center; gap: 6px;
  padding: 11px 16px; font-size: 13px; font-weight: 500;
  color: var(--t-muted); background: none; border: none;
  border-bottom: 2px solid transparent; cursor: pointer;
  transition: all 0.15s; white-space: nowrap; font-family: inherit;
  margin-bottom: -1px;
}
.pd-tab:hover { color: var(--t-primary); }
.pd-tab.active { color: var(--accent); border-bottom-color: var(--accent); font-weight: 600; }
.pd-tab-icon { display: flex; align-items: center; }

/* Tab content */
.pd-tab-content { min-height: calc(100vh - 104px); }

/* ── Mobile ─────────────────────────────────────────── */
@media (max-width: 600px) {
  .pd-topbar { padding: 0 12px; gap: 6px; }
  .pd-project-name { max-width: 120px; font-size: 13px; }
  .pd-back-btn span { display: none; }
  .pd-tab { padding: 9px 10px; font-size: 12px; gap: 4px; }
  .pd-tab-icon svg { display: none; }
  /* Hide export btn on mobile */
  .pd-topbar .btn-v2-ghost { display: none; }
}
</style>
