<template>
  <div class="rehearsal-tab">
    <!-- Start new rehearsal -->
    <div class="tab-header">
      <button class="btn-v2 btn-v2-primary" @click="goRehearsal" :disabled="!planId">
        <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="6.5" cy="6.5" r="5"/><path d="M4.5 6.5a2 2 0 1 0 4 0 2 2 0 0 0-4 0"/>
        </svg>
        开始新排练
      </button>
      <span v-if="!planId" class="hint">请先生成讲解方案，再进行排练</span>
    </div>

    <!-- History list -->
    <div v-if="loading" class="list-loading">
      <el-skeleton :rows="3" animated />
    </div>

    <div v-else-if="rehearsals.length === 0" class="empty-state">
      <div class="empty-icon">
        <svg width="40" height="40" viewBox="0 0 40 40" fill="none" stroke="var(--t-faint)" stroke-width="1.5">
          <circle cx="20" cy="20" r="16"/><polygon points="15 13 30 20 15 27" fill="var(--t-faint)" stroke="none"/>
        </svg>
      </div>
      <p>暂无排练记录，快去开始第一次排练吧！</p>
    </div>

    <div v-else class="rehearsal-list">
      <div
        v-for="r in rehearsals"
        :key="r.rehearsal_id"
        class="rehearsal-row"
        @click="goReport(r.rehearsal_id)"
      >
        <!-- Left: fixed-width score column -->
        <div class="row-score">
          <template v-if="r.total_score != null">
            <span class="score-num" :class="scoreClass(r.total_score)">{{ r.total_score.toFixed(1) }}</span>
            <span class="score-unit">分</span>
          </template>
          <template v-else>
            <span class="status-badge" :class="`status-${r.status}`">{{ statusLabel(r.status) }}</span>
          </template>
        </div>

        <!-- Middle: time + duration -->
        <div class="row-info">
          <div class="row-time">{{ formatDate(r.created_at) }}</div>
          <div class="row-duration">时长 {{ formatDuration(r.audio_duration) }}</div>
        </div>

        <!-- Right: arrow -->
        <svg class="row-arrow" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="var(--t-faint)" stroke-width="2">
          <polyline points="6 3 11 8 6 13"/>
        </svg>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Microphone, ArrowRight } from '@element-plus/icons-vue'
import { rehearsalApi, type RehearsalListItem } from '@/api/rehearsal'

const props = defineProps<{ taskId: number; planId: number | null }>()
const router = useRouter()

const rehearsals = ref<RehearsalListItem[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await rehearsalApi.listByTask(props.taskId)
    rehearsals.value = res.data
  } catch { /* ignore */ } finally {
    loading.value = false
  }
})

function goRehearsal() {
  router.push({
    name: 'rehearsal',
    query: { taskId: props.taskId, planId: props.planId ?? undefined },
  })
}

function goReport(id: number) {
  router.push({ name: 'report', params: { id } })
}

function scoreClass(score: number) {
  if (score >= 80) return 'good'
  if (score >= 60) return 'ok'
  return 'bad'
}

function statusLabel(status: number) {
  const map: Record<number, string> = {
    0: '录制中',
    1: '转录中',
    2: '评分中',
    3: '已评分',
    4: '已提交审核',
    5: '已认证',
    6: '需改进',
  }
  return map[status] ?? '未知'
}

function statusTagType(status: number): '' | 'success' | 'warning' | 'danger' | 'info' {
  if (status === 3 || status === 4 || status === 5) return 'success'
  if (status === 6) return 'warning'
  if (status <= 2) return 'info'
  return ''
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

function formatDuration(sec: number) {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return m > 0 ? `${m}分${s}秒` : `${s}秒`
}
</script>

<style scoped>
.rehearsal-tab { padding: 20px 24px; }

.tab-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.hint { font-size: 13px; color: var(--t-faint); }

.list-loading { padding: 16px; }

/* Empty state */
.empty-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 60px 0; gap: 12px; color: var(--t-faint);
}
.empty-icon { opacity: 0.4; }
.empty-state p { font-size: 14px; margin: 0; }

/* List */
.rehearsal-list {
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.rehearsal-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 20px;
  cursor: pointer;
  border-bottom: 1px solid var(--border);
  transition: background 0.15s;
}
.rehearsal-row:last-child { border-bottom: none; }
.rehearsal-row:hover { background: var(--bg-content); }

/* Fixed-width score column — keeps info column always at same x */
.row-score {
  display: flex;
  align-items: baseline;
  gap: 3px;
  width: 80px;
  flex-shrink: 0;
}

.score-num { font-size: 28px; font-weight: 700; line-height: 1; }
.score-num.good { color: var(--green); }
.score-num.ok   { color: var(--orange); }
.score-num.bad  { color: var(--red); }
.score-unit { font-size: 12px; color: var(--t-faint); }

/* Status badge when no score yet */
.status-badge {
  display: inline-flex; align-items: center;
  font-size: 11px; font-weight: 500; padding: 2px 8px;
  border-radius: 20px; white-space: nowrap;
}
.status-0, .status-1, .status-2 { background: #EEF2FF; color: #6366F1; }
.status-3, .status-4, .status-5 { background: #F0FDF4; color: #16A34A; }
.status-6 { background: #FFF7ED; color: #C2410C; }

.row-info { flex: 1; }
.row-time { font-size: 14px; font-weight: 500; color: var(--t-primary); }
.row-duration { font-size: 12px; color: var(--t-faint); margin-top: 2px; }

.row-arrow { flex-shrink: 0; }
</style>
