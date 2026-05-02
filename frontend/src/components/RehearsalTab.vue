<template>
  <div class="rehearsal-tab">
    <!-- Start new rehearsal -->
    <div class="tab-header">
      <el-button type="primary" :icon="Microphone" @click="goRehearsal" :disabled="!planId">
        开始新排练
      </el-button>
      <span v-if="!planId" class="hint">请先生成讲解方案，再进行排练</span>
    </div>

    <!-- History list -->
    <div v-if="loading" class="list-loading">
      <el-skeleton :rows="3" animated />
    </div>

    <el-empty v-else-if="rehearsals.length === 0" description="暂无排练记录，快去开始第一次排练吧！" />

    <div v-else class="rehearsal-list">
      <el-card
        v-for="r in rehearsals"
        :key="r.rehearsal_id"
        shadow="hover"
        class="rehearsal-card"
        @click="goReport(r.rehearsal_id)"
      >
        <div class="card-main">
          <div class="card-score">
            <template v-if="r.total_score != null">
              <span class="score-num" :class="scoreClass(r.total_score)">
                {{ r.total_score.toFixed(1) }}
              </span>
              <span class="score-unit">分</span>
            </template>
            <template v-else>
              <el-tag :type="statusTagType(r.status)" size="small">
                {{ statusLabel(r.status) }}
              </el-tag>
            </template>
          </div>

          <div class="card-info">
            <div class="card-time">{{ formatDate(r.created_at) }}</div>
            <div class="card-duration">时长 {{ formatDuration(r.audio_duration) }}</div>
          </div>

          <el-icon class="card-arrow"><ArrowRight /></el-icon>
        </div>
      </el-card>
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
.rehearsal-tab { padding: 16px 0; }

.tab-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.hint { font-size: 13px; color: #909399; }

.list-loading { padding: 16px; }

.rehearsal-list { display: flex; flex-direction: column; gap: 12px; }

.rehearsal-card { cursor: pointer; transition: transform 0.15s; }
.rehearsal-card:hover { transform: translateY(-2px); }

.card-main {
  display: flex;
  align-items: center;
  gap: 16px;
}

.card-score {
  display: flex;
  align-items: baseline;
  gap: 4px;
  min-width: 80px;
}

.score-num { font-size: 32px; font-weight: 700; }
.score-num.good { color: #67C23A; }
.score-num.ok { color: #E6A23C; }
.score-num.bad { color: #F56C6C; }
.score-unit { font-size: 14px; color: #909399; }

.card-info { flex: 1; }
.card-time { font-size: 14px; color: #303133; }
.card-duration { font-size: 13px; color: #909399; margin-top: 4px; }

.card-arrow { color: #c0c4cc; }
</style>
