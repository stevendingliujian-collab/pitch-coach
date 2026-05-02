<template>
  <div class="report-page">
    <div class="page-header">
      <el-button :icon="ArrowLeft" @click="router.back()" text>返回</el-button>
      <h2>排练评分报告</h2>
    </div>

    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="10" animated />
    </div>

    <div v-else-if="!report" class="empty-state">
      <el-empty description="报告不存在或评分尚未完成" />
      <el-button @click="router.back()">返回</el-button>
    </div>

    <template v-else>
      <!-- Score overview -->
      <el-row :gutter="24" class="score-overview">
        <el-col :span="6">
          <el-card shadow="never" class="total-score-card">
            <div class="total-score">{{ report.total_score?.toFixed(1) ?? '--' }}</div>
            <div class="score-label">综合得分</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <ScoreDimCard
            label="流畅度"
            desc="填充词控制"
            :score="report.fluency_score ?? undefined"
            color="#67C23A"
          />
        </el-col>
        <el-col :span="6">
          <ScoreDimCard
            label="语速"
            desc="字/分钟节奏"
            :score="report.rate_score ?? undefined"
            color="#409EFF"
          />
        </el-col>
        <el-col :span="6">
          <ScoreDimCard
            label="时间控制"
            desc="时长 & 重点分配"
            :score="report.timing_score ?? undefined"
            color="#E6A23C"
          />
        </el-col>
      </el-row>

      <!-- Stats row -->
      <el-row :gutter="16" class="stats-row">
        <el-col :span="6">
          <div class="stat-item">
            <span class="stat-value">{{ formatDuration(report.total_duration_sec) }}</span>
            <span class="stat-label">总时长</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <span class="stat-value">{{ report.chars_per_min?.toFixed(0) ?? '--' }}</span>
            <span class="stat-label">字/分钟</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <span class="stat-value" :class="report.filler_count! > 10 ? 'warn' : 'good'">
              {{ report.filler_count ?? '--' }}
            </span>
            <span class="stat-label">填充词总数</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <span class="stat-value">{{ report.page_timings.length }}</span>
            <span class="stat-label">共翻页次数</span>
          </div>
        </el-col>
      </el-row>

      <!-- Audio player -->
      <el-card shadow="never" class="audio-card">
        <template #header>录音回放</template>
        <audio :src="report.audio_url" controls style="width:100%" />
      </el-card>

      <!-- Improvement tips -->
      <el-card shadow="never" class="tips-card" v-if="report.improvement_tips.length">
        <template #header>AI 改进建议</template>
        <div v-for="(tip, i) in report.improvement_tips" :key="i" class="tip-item">
          <el-icon color="#E6A23C"><WarningFilled /></el-icon>
          <span>{{ tip }}</span>
        </div>
      </el-card>

      <!-- Filler word detail -->
      <el-card shadow="never" class="filler-card" v-if="report.filler_detail.length">
        <template #header>填充词明细</template>
        <div class="filler-chips">
          <el-tag
            v-for="f in sortedFillers"
            :key="f.word"
            :type="f.count > 5 ? 'danger' : f.count > 2 ? 'warning' : 'info'"
            class="filler-chip"
          >
            「{{ f.word }}」× {{ f.count }}
          </el-tag>
        </div>
      </el-card>

      <!-- Page timing timeline -->
      <el-card shadow="never" class="timeline-card" v-if="report.page_scores.length">
        <template #header>逐页时间分析</template>
        <div class="page-timeline">
          <div
            v-for="ps in report.page_scores"
            :key="ps.page_number"
            class="page-bar-row"
          >
            <span class="page-label">P{{ ps.page_number }}</span>
            <div class="bar-wrap">
              <div
                class="bar-fill"
                :class="{ ok: ps.timing_ok, warn: !ps.timing_ok }"
                :style="{ width: barWidth(ps) + '%' }"
              />
              <div
                class="bar-target"
                :style="{ left: 0, width: targetWidth(ps) + '%' }"
              />
            </div>
            <span class="page-dur">{{ ps.actual_duration_sec.toFixed(0) }}s</span>
            <el-icon v-if="ps.timing_ok" color="#67C23A"><SuccessFilled /></el-icon>
            <el-icon v-else color="#E6A23C"><WarningFilled /></el-icon>
          </div>
        </div>
      </el-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, defineComponent, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, WarningFilled, SuccessFilled } from '@element-plus/icons-vue'
import { rehearsalApi, type RehearsalReport } from '@/api/rehearsal'

const route = useRoute()
const router = useRouter()
const rehearsalId = Number(route.params.id)

const loading = ref(true)
const report = ref<RehearsalReport | null>(null)

onMounted(async () => {
  try {
    const res = await rehearsalApi.getReport(rehearsalId)
    report.value = res.data
  } catch { /* 404 or not scored yet */ } finally {
    loading.value = false
  }
})

const sortedFillers = computed(() =>
  [...(report.value?.filler_detail ?? [])].sort((a, b) => b.count - a.count)
)

const maxActual = computed(() =>
  Math.max(...(report.value?.page_scores ?? []).map((p) => p.actual_duration_sec), 1)
)

function barWidth(ps: { actual_duration_sec: number }) {
  return Math.min(100, (ps.actual_duration_sec / maxActual.value) * 100)
}
function targetWidth(ps: { suggested_duration_sec: number }) {
  return Math.min(100, (ps.suggested_duration_sec / maxActual.value) * 100)
}

function formatDuration(sec: number | null) {
  if (!sec) return '--'
  const m = Math.floor(sec / 60)
  const s = Math.round(sec % 60)
  return m > 0 ? `${m}分${s}秒` : `${s}秒`
}

// Inline sub-component for score dimension cards
const ScoreDimCard = defineComponent({
  props: { label: String, desc: String, score: Number, color: String },
  setup(props) {
    return () =>
      h('div', { class: 'dim-card' }, [
        h('div', { class: 'dim-score', style: { color: props.color } },
          props.score != null ? props.score.toFixed(1) : '--'
        ),
        h('div', { class: 'dim-label' }, props.label),
        h('div', { class: 'dim-desc' }, props.desc),
        h('el-progress', {
          percentage: props.score ?? 0,
          strokeWidth: 6,
          showText: false,
          color: props.color,
          style: 'margin-top:8px',
        }),
      ])
  },
})
</script>

<style scoped>
.report-page { padding: 24px; max-width: 1100px; margin: 0 auto; }

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}
.page-header h2 { margin: 0; font-size: 20px; }

.loading-state, .empty-state { padding: 48px; text-align: center; }

.score-overview { margin-bottom: 16px; }

.total-score-card {
  text-align: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
}
.total-score { font-size: 48px; font-weight: 700; line-height: 1; }
.score-label { font-size: 14px; margin-top: 6px; opacity: 0.9; }

.dim-card {
  padding: 16px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  height: 100%;
}
.dim-score { font-size: 36px; font-weight: 700; line-height: 1; }
.dim-label { font-size: 14px; font-weight: 600; margin-top: 4px; }
.dim-desc { font-size: 12px; color: #909399; }

.stats-row {
  margin-bottom: 16px;
}
.stat-item {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.stat-value { font-size: 24px; font-weight: 700; }
.stat-value.warn { color: #E6A23C; }
.stat-value.good { color: #67C23A; }
.stat-label { font-size: 12px; color: #909399; margin-top: 4px; }

.audio-card, .tips-card, .filler-card, .timeline-card { margin-bottom: 16px; }

.tip-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 0;
  font-size: 14px;
  border-bottom: 1px solid #f0f0f0;
}
.tip-item:last-child { border-bottom: none; }

.filler-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.filler-chip { font-size: 13px; }

.page-timeline { display: flex; flex-direction: column; gap: 10px; }
.page-bar-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.page-label { width: 28px; font-size: 12px; color: #606266; flex-shrink: 0; }
.bar-wrap {
  flex: 1;
  height: 14px;
  background: #f0f2f5;
  border-radius: 4px;
  position: relative;
  overflow: hidden;
}
.bar-fill {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  border-radius: 4px;
  transition: width 0.4s ease;
}
.bar-fill.ok { background: #67C23A; opacity: 0.8; }
.bar-fill.warn { background: #E6A23C; opacity: 0.8; }
.bar-target {
  position: absolute;
  top: 0;
  height: 100%;
  border-right: 2px dashed #909399;
  pointer-events: none;
}
.page-dur { width: 36px; font-size: 12px; color: #606266; text-align: right; }
</style>
