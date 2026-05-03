<template>
  <div class="readiness-tab">
    <!-- Header: progress ring + summary -->
    <div class="rt-header">
      <div class="rt-ring-wrap">
        <svg class="rt-ring" viewBox="0 0 88 88">
          <circle cx="44" cy="44" r="36" fill="none" stroke="#E5E7EB" stroke-width="6"/>
          <circle
            cx="44" cy="44" r="36"
            fill="none"
            :stroke="ringColor"
            stroke-width="6"
            stroke-linecap="round"
            :stroke-dasharray="`${2 * Math.PI * 36}`"
            :stroke-dashoffset="`${2 * Math.PI * 36 * (1 - (readiness?.progress_pct ?? 0) / 100)}`"
            transform="rotate(-90 44 44)"
            style="transition: stroke-dashoffset 0.8s ease;"
          />
        </svg>
        <div class="rt-ring-num">{{ readiness?.progress_pct ?? 0 }}%</div>
      </div>

      <div class="rt-summary">
        <div class="rt-summary-title">述标就绪度</div>
        <div class="rt-summary-steps">
          <span class="done-count">{{ readiness?.done_count ?? 0 }}</span>
          <span class="dim"> / {{ readiness?.total_steps ?? 7 }} 步已完成</span>
        </div>
        <div class="rt-bid-date" v-if="readiness?.bid_date">
          <svg width="13" height="13" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.7">
            <rect x="1" y="2" width="12" height="11" rx="1.5"/>
            <line x1="4" y1="1" x2="4" y2="3"/><line x1="10" y1="1" x2="10" y2="3"/>
            <line x1="1" y1="5" x2="13" y2="5"/>
          </svg>
          述标日期：{{ formatDate(readiness.bid_date) }}
          <span :class="['days-badge', daysClass]">{{ daysLeft }}</span>
        </div>
        <div class="rt-outcome-wrap" v-if="task">
          <span class="outcome-label">述标结果：</span>
          <span v-if="task.result" :class="['outcome-badge', outcomeClass(task.result)]">
            {{ outcomeText(task.result) }}
          </span>
          <span v-else class="outcome-empty">未标记</span>
          <button class="btn-mark" @click="showOutcomeMenu = !showOutcomeMenu">标记结果</button>
          <div v-if="showOutcomeMenu" class="outcome-menu">
            <button v-for="opt in outcomeOptions" :key="opt.value"
              class="outcome-opt" :class="`opt-${opt.cls}`"
              @click="setOutcome(opt.value)">
              {{ opt.label }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Steps list -->
    <div v-if="loading" class="rt-loading">
      <div class="spinner"></div> 加载中…
    </div>
    <div v-else-if="readiness" class="rt-steps">
      <div
        v-for="(step, idx) in readiness.steps"
        :key="step.key"
        class="rt-step"
        :class="{ done: step.done, pending: !step.done }"
      >
        <div class="step-num-wrap">
          <div class="step-num" :class="{ done: step.done }">
            <svg v-if="step.done" width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="white" stroke-width="2.5">
              <polyline points="2.5 7 5.5 10.5 11.5 3.5"/>
            </svg>
            <span v-else>{{ idx + 1 }}</span>
          </div>
          <div v-if="idx < readiness.steps.length - 1" class="step-connector" :class="{ done: step.done }"/>
        </div>

        <div class="step-body">
          <div class="step-label">{{ step.label }}</div>
          <div class="step-desc">{{ step.desc }}</div>
          <button
            v-if="!step.done && step.action_tab"
            class="step-action"
            @click="$emit('switchTab', step.action_tab)"
          >
            去完成 →
          </button>
        </div>
      </div>
    </div>

    <!-- Outcome picker click-outside closer -->
    <div v-if="showOutcomeMenu" class="outcome-overlay" @click="showOutcomeMenu = false"/>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { pitchTaskApi, type PitchTask, type TaskReadiness } from '@/api/pitchTask'
import dayjs from 'dayjs'

const props = defineProps<{
  taskId: number
  task: PitchTask | null
}>()

const emit = defineEmits<{
  (e: 'switchTab', tab: string): void
  (e: 'taskUpdated', task: PitchTask): void
}>()

const loading = ref(false)
const readiness = ref<TaskReadiness | null>(null)
const showOutcomeMenu = ref(false)

const outcomeOptions = [
  { value: 1, label: '✅ 中标', cls: 'won' },
  { value: 2, label: '❌ 未中标', cls: 'lost' },
  { value: 3, label: '🚫 弃标', cls: 'withdrawn' },
  { value: 4, label: '⚠️ 流标', cls: 'void' },
]

const ringColor = computed(() => {
  const p = readiness.value?.progress_pct ?? 0
  if (p >= 80) return '#22C55E'
  if (p >= 50) return '#F59E0B'
  return '#EF4444'
})

const daysLeft = computed(() => {
  if (!readiness.value?.bid_date) return ''
  const diff = dayjs(readiness.value.bid_date).diff(dayjs(), 'day')
  if (diff < 0) return '已过期'
  if (diff === 0) return '今天述标'
  return `还剩 ${diff} 天`
})

const daysClass = computed(() => {
  if (!readiness.value?.bid_date) return ''
  const diff = dayjs(readiness.value.bid_date).diff(dayjs(), 'day')
  if (diff < 0) return 'expired'
  if (diff <= 3) return 'urgent'
  if (diff <= 7) return 'soon'
  return 'ok'
})

function outcomeText(result: number): string {
  return { 1: '中标 ✅', 2: '未中标 ❌', 3: '弃标', 4: '流标' }[result] ?? '未知'
}

function outcomeClass(result: number): string {
  return { 1: 'won', 2: 'lost', 3: 'withdrawn', 4: 'void' }[result] ?? ''
}

async function setOutcome(result: number) {
  showOutcomeMenu.value = false
  if (!props.task) return
  try {
    const res = await pitchTaskApi.setOutcome(props.taskId, result)
    emit('taskUpdated', res.data)
    ElMessage.success('已标记结果')
  } catch {
    ElMessage.error('标记失败')
  }
}

function formatDate(iso: string): string {
  return dayjs(iso).format('YYYY年M月D日')
}

onMounted(async () => {
  loading.value = true
  try {
    const res = await pitchTaskApi.readiness(props.taskId)
    readiness.value = res.data
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.readiness-tab { padding: 28px 32px; max-width: 680px; }

/* Header */
.rt-header {
  display: flex; align-items: flex-start; gap: 28px; margin-bottom: 32px;
  background: white; border-radius: 14px; border: 1px solid #e5e7eb; padding: 24px;
}

.rt-ring-wrap { position: relative; flex-shrink: 0; }
.rt-ring { width: 88px; height: 88px; }
.rt-ring-num {
  position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
  font-size: 22px; font-weight: 800; color: #1a1a2e;
}

.rt-summary { flex: 1; }
.rt-summary-title { font-size: 15px; font-weight: 700; color: #1a1a2e; margin-bottom: 4px; }
.rt-summary-steps { font-size: 14px; color: #6b7280; margin-bottom: 10px; }
.done-count { font-size: 18px; font-weight: 800; color: #6366F1; }
.dim { color: #9ca3af; }

.rt-bid-date {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; color: #6b7280; margin-bottom: 10px;
}

.days-badge {
  padding: 1px 7px; border-radius: 10px; font-size: 11px; font-weight: 700;
}
.days-badge.ok        { background: #DCFCE7; color: #16a34a; }
.days-badge.soon      { background: #FEF3C7; color: #92400E; }
.days-badge.urgent    { background: #FEE2E2; color: #DC2626; }
.days-badge.expired   { background: #F3F4F6; color: #9ca3af; }

/* Outcome */
.rt-outcome-wrap {
  display: flex; align-items: center; gap: 8px;
  font-size: 12px; color: #6b7280; position: relative;
}
.outcome-label { font-weight: 600; }
.outcome-badge { padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 700; }
.outcome-badge.won        { background: #DCFCE7; color: #16a34a; }
.outcome-badge.lost       { background: #FEE2E2; color: #DC2626; }
.outcome-badge.withdrawn  { background: #F3F4F6; color: #6b7280; }
.outcome-badge.void       { background: #FEF3C7; color: #92400E; }
.outcome-empty { color: #9ca3af; font-style: italic; }

.btn-mark {
  padding: 3px 10px; background: #eff6ff; color: #2563eb; border: none;
  border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer;
}
.btn-mark:hover { background: #dbeafe; }

.outcome-menu {
  position: absolute; top: 100%; left: 60px; background: white;
  border: 1px solid #e5e7eb; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.12);
  z-index: 10; min-width: 130px; overflow: hidden; margin-top: 4px;
}
.outcome-opt {
  display: block; width: 100%; padding: 8px 14px; background: none; border: none;
  text-align: left; font-size: 13px; cursor: pointer; transition: background 0.1s;
}
.outcome-opt:hover { background: #f9fafb; }
.outcome-overlay { position: fixed; inset: 0; z-index: 9; }

/* Loading */
.rt-loading { display: flex; align-items: center; gap: 10px; color: #6b7280; padding: 40px 0; }
.spinner { width: 18px; height: 18px; border: 2px solid #e5e7eb; border-top-color: #6366F1; border-radius: 50%; animation: spin 0.6s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Steps */
.rt-steps { display: flex; flex-direction: column; }

.rt-step {
  display: flex; gap: 16px; align-items: flex-start;
}

.step-num-wrap {
  display: flex; flex-direction: column; align-items: center;
  flex-shrink: 0; padding-top: 2px;
}

.step-num {
  width: 28px; height: 28px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700;
  background: #f3f4f6; color: #9ca3af;
  flex-shrink: 0;
}
.step-num.done { background: #6366F1; color: white; }

.step-connector {
  width: 2px; flex: 1; background: #e5e7eb; margin: 4px 0;
  min-height: 16px;
}
.step-connector.done { background: #c7d2fe; }

.step-body {
  padding-bottom: 20px; flex: 1;
}
.rt-step:last-child .step-body { padding-bottom: 0; }

.step-label { font-size: 14px; font-weight: 600; color: #1a1a2e; margin-bottom: 3px; }
.rt-step.done .step-label { color: #16a34a; }
.step-desc { font-size: 12px; color: #9ca3af; }

.step-action {
  margin-top: 6px; padding: 4px 10px; background: #eff6ff; color: #2563eb;
  border: none; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer;
}
.step-action:hover { background: #dbeafe; }

/* Mobile */
@media (max-width: 600px) {
  .readiness-tab { padding: 16px; }
  .rt-header { flex-direction: column; gap: 16px; padding: 16px; }
}
</style>
