<template>
  <div class="dp-page">
    <!-- Header -->
    <div class="dp-header">
      <div class="dp-header-left">
        <el-button :icon="ArrowLeft" text @click="router.push('/projects')">返回</el-button>
        <span class="dp-title">每日微练习</span>
      </div>
      <div class="dp-streak" v-if="streakInfo">
        <span class="streak-flame">🔥</span>
        <span class="streak-num">{{ streakInfo.current_streak }}</span>
        <span class="streak-label">天连续</span>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="dp-loading">
      <el-skeleton :rows="5" animated />
    </div>

    <!-- Main content -->
    <div v-else-if="today" class="dp-content">

      <!-- Practice card -->
      <div class="practice-card" :class="{ 'is-done': today.status === 1 && recState !== 'scored' }">
        <div class="practice-meta">
          <el-tag :type="typeTagType(today.practice_type)" size="small" round>
            {{ typeLabel(today.practice_type) }}
          </el-tag>
          <span class="practice-weekday">{{ weekdayLabel }}</span>
          <el-tag v-if="today.status === 1 && recState !== 'scored'" type="success" size="small">✓ 今日已完成</el-tag>
        </div>

        <h2 class="practice-title">{{ today.title }}</h2>

        <div class="practice-instruction">
          <pre class="instruction-text">{{ today.instruction }}</pre>
        </div>

        <div class="practice-target">
          <el-icon><Timer /></el-icon>
          目标时长：<strong>{{ today.target_duration_sec }} 秒</strong>
        </div>

        <div v-if="today.key_points.length" class="key-points">
          <span class="key-points-label">评分关键点：</span>
          <el-tag
            v-for="kp in today.key_points"
            :key="kp"
            size="small"
            effect="plain"
            class="kp-tag"
          >{{ kp }}</el-tag>
        </div>
      </div>

      <!-- Recording panel -->
      <div class="recording-panel">

        <!-- idle -->
        <template v-if="recState === 'idle'">
          <el-button
            type="primary"
            :icon="Microphone"
            round
            size="large"
            :loading="starting"
            @click="startRecording"
          >
            {{ today.status === 1 ? '再练一次' : '开始录音' }}
          </el-button>
          <p class="record-hint">点击开始，系统将自动计时并在完成后评分</p>
        </template>

        <!-- recording -->
        <template v-else-if="recState === 'recording'">
          <div class="recording-active">
            <div class="rec-pulse" />
            <div class="rec-timer">{{ formatTime(elapsed) }}</div>
            <div class="rec-target-bar">
              <div
                class="rec-target-fill"
                :style="{ width: Math.min((elapsed / today.target_duration_sec) * 100, 100) + '%' }"
                :class="{ overshoot: elapsed > today.target_duration_sec }"
              />
            </div>
            <div class="rec-target-label">
              目标 {{ today.target_duration_sec }}s
              <span v-if="elapsed > today.target_duration_sec" class="overshoot-text">
                已超 {{ elapsed - today.target_duration_sec }}s
              </span>
            </div>
            <el-button type="danger" round :loading="stopping" @click="stopAndScore">
              完成录音
            </el-button>
          </div>
        </template>

        <!-- uploading -->
        <template v-else-if="recState === 'uploading'">
          <div class="uploading-state">
            <el-progress type="circle" :percentage="uploadPct" :width="80" />
            <p>上传并评分中…</p>
          </div>
        </template>

        <!-- scored -->
        <template v-else-if="recState === 'scored' && scoreResult">
          <div class="score-panel">
            <div class="score-circle" :class="scoreClass(scoreResult.total_score)">
              <span class="score-num">{{ scoreResult.total_score.toFixed(0) }}</span>
              <span class="score-unit">分</span>
            </div>

            <div class="score-dims">
              <div class="dim-item">
                <span class="dim-icon">⏱</span>
                <span>{{ scoreResult.timing_sec }}s / 目标{{ today.target_duration_sec }}s</span>
              </div>
              <div class="dim-item">
                <span class="dim-icon">🗣</span>
                <span>填充词 {{ scoreResult.filler_count }} 次</span>
              </div>
              <div class="dim-item">
                <span class="dim-icon">✅</span>
                <span>关键点覆盖 {{ Math.round(scoreResult.keyword_hit_rate * 100) }}%</span>
              </div>
            </div>

            <div class="feedback-list">
              <div v-for="(f, i) in scoreResult.feedback" :key="i" class="feedback-item">
                {{ f }}
              </div>
            </div>

            <div v-if="scoreResult.current_streak > 0" class="streak-badge" :class="{ 'new-record': scoreResult.is_new_record }">
              <span>🔥 连续练习 {{ scoreResult.current_streak }} 天</span>
              <span v-if="scoreResult.is_new_record" class="new-record-badge">新纪录！</span>
            </div>

            <el-collapse v-if="scoreResult.reference_answer" class="ref-answer">
              <el-collapse-item name="ref">
                <template #title>
                  <span class="ref-title">📖 参考答案</span>
                </template>
                <div class="ref-content">{{ scoreResult.reference_answer }}</div>
              </el-collapse-item>
            </el-collapse>

            <el-button class="redo-btn" round @click="resetForRedo">再练一次</el-button>
          </div>
        </template>

      </div>

      <!-- History mini-strip -->
      <div class="history-strip" v-if="history.length">
        <h3 class="history-title">最近 {{ history.length }} 次练习</h3>
        <div class="history-list">
          <div
            v-for="item in history"
            :key="item.log_id"
            class="history-dot"
            :class="item.total_score !== null ? scoreClass(item.total_score) : 'score-mid'"
            :title="`${item.practice_date} ${item.title} ${item.total_score?.toFixed(0) ?? '--'}分`"
          >
            <span class="dot-date">{{ item.practice_date.slice(5) }}</span>
            <span class="dot-score">{{ item.total_score?.toFixed(0) ?? '–' }}</span>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Microphone, Timer } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  dailyPracticeApi,
  type TodayPractice,
  type PracticeScoreResponse,
  type PracticeHistoryItem,
  type StreakInfo,
} from '@/api/dailyPractice'

const router = useRouter()

// ─── state ───────────────────────────────────────────────────────────────────
const loading    = ref(true)
const today      = ref<TodayPractice | null>(null)
const streakInfo = ref<StreakInfo | null>(null)
const history    = ref<PracticeHistoryItem[]>([])
const scoreResult= ref<PracticeScoreResponse | null>(null)

type RecState = 'idle' | 'recording' | 'uploading' | 'scored'
const recState  = ref<RecState>('idle')
const starting  = ref(false)
const stopping  = ref(false)
const uploadPct = ref(0)
const elapsed   = ref(0)

// ─── recording internals ─────────────────────────────────────────────────────
let mediaRecorder: MediaRecorder | null = null
let audioChunks: Blob[] = []
let currentLogId = 0
let currentObjectKey = ''
let currentUploadUrl = ''
let timerHandle: ReturnType<typeof setInterval> | null = null

// ─── lifecycle ────────────────────────────────────────────────────────────────
onMounted(async () => {
  try {
    const [todayRes, histRes, streakRes] = await Promise.all([
      dailyPracticeApi.getToday(),
      dailyPracticeApi.getHistory(10),
      dailyPracticeApi.getStreak(),
    ])
    today.value      = todayRes.data
    history.value    = histRes.data
    streakInfo.value = streakRes.data
  } catch {
    ElMessage.error('加载练习内容失败')
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  stopTimer()
  if (mediaRecorder?.state === 'recording') {
    mediaRecorder.stop()
    mediaRecorder.stream.getTracks().forEach(t => t.stop())
  }
})

// ─── computed ─────────────────────────────────────────────────────────────────
const weekdayLabel = computed(() => {
  const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
  const d = new Date().getDay()
  return days[d === 0 ? 6 : d - 1]
})

// ─── methods ──────────────────────────────────────────────────────────────────
async function startRecording() {
  if (!today.value) return
  starting.value = true
  try {
    // Get presigned URL
    const res = await dailyPracticeApi.start(today.value.item_id)
    currentLogId      = res.data.log_id
    currentObjectKey  = res.data.object_key
    currentUploadUrl  = res.data.upload_url

    // Access microphone
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' })
    audioChunks = []
    mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data) }
    mediaRecorder.start(200)

    // Start timer
    elapsed.value = 0
    timerHandle = setInterval(() => { elapsed.value++ }, 1000)
    recState.value = 'recording'
  } catch (err: any) {
    ElMessage.error('无法访问麦克风：' + (err?.message ?? '请检查浏览器权限'))
  } finally {
    starting.value = false
  }
}

async function stopAndScore() {
  if (!mediaRecorder) return
  stopping.value = true
  stopTimer()

  const durationSec = elapsed.value

  try {
    // Stop recorder
    await new Promise<void>((resolve) => {
      mediaRecorder!.onstop = () => resolve()
      mediaRecorder!.stop()
      mediaRecorder!.stream.getTracks().forEach(t => t.stop())
    })

    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' })
    recState.value = 'uploading'
    uploadPct.value = 0

    // Upload to MinIO / OSS
    await dailyPracticeApi.uploadAudio(
      currentUploadUrl,
      audioBlob,
      (pct) => { uploadPct.value = Math.min(pct, 90) },
    )
    uploadPct.value = 95

    // Submit to backend for scoring
    const completeRes = await dailyPracticeApi.complete({
      log_id: currentLogId,
      object_key: currentObjectKey,
      audio_duration_sec: durationSec,
    })
    uploadPct.value = 100

    scoreResult.value = completeRes.data
    streakInfo.value = {
      current_streak:  completeRes.data.current_streak,
      longest_streak:  completeRes.data.longest_streak,
      total_practices: (streakInfo.value?.total_practices ?? 0) + 1,
      last_practice_date: new Date().toISOString().slice(0, 10),
    }

    if (today.value) today.value.status = 1
    recState.value = 'scored'

    // Refresh history
    const histRes = await dailyPracticeApi.getHistory(10)
    history.value = histRes.data
  } catch (err: any) {
    ElMessage.error('提交失败：' + (err?.message ?? '请重试'))
    recState.value = 'idle'
  } finally {
    stopping.value = false
  }
}

function stopTimer() {
  if (timerHandle) { clearInterval(timerHandle); timerHandle = null }
}

function resetForRedo() {
  scoreResult.value = null
  recState.value    = 'idle'
  elapsed.value     = 0
}

function formatTime(sec: number) {
  const m = Math.floor(sec / 60).toString().padStart(2, '0')
  const s = (sec % 60).toString().padStart(2, '0')
  return `${m}:${s}`
}

function typeLabel(type: string) {
  return ({
    intro: '公司介绍', case: '案例讲解', term: '术语解释',
    qa: '评委问答', competitive: '竞品话术', review: '综合复习',
  } as Record<string, string>)[type] ?? type
}

function typeTagType(type: string): 'primary' | 'success' | 'warning' | 'info' | 'danger' {
  return ({
    intro: 'primary', case: 'success', term: 'info',
    qa: 'warning', competitive: 'danger', review: 'info',
  } as Record<string, 'primary' | 'success' | 'warning' | 'info' | 'danger'>)[type] ?? 'info'
}

function scoreClass(score: number) {
  if (score >= 85) return 'score-high'
  if (score >= 70) return 'score-mid'
  return 'score-low'
}
</script>

<style scoped>
.dp-page {
  min-height: 100vh;
  background: #f4f6fa;
}

/* ── Header ── */
.dp-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: #fff;
  border-bottom: 1px solid #e4e7ef;
  position: sticky;
  top: 0;
  z-index: 10;
}
.dp-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.dp-title {
  font-size: 18px;
  font-weight: 700;
  color: #1a1a2e;
}
.dp-streak {
  display: flex;
  align-items: center;
  gap: 4px;
  background: #fff7e6;
  border: 1px solid #ffd591;
  border-radius: 20px;
  padding: 4px 14px;
}
.streak-flame { font-size: 18px; }
.streak-num   { font-size: 22px; font-weight: 800; color: #fa8c16; line-height: 1; }
.streak-label { font-size: 13px; color: #ad6800; }

/* ── Loading ── */
.dp-loading { max-width: 640px; margin: 40px auto; padding: 0 20px; }

/* ── Layout ── */
.dp-content {
  max-width: 640px;
  margin: 0 auto;
  padding: 24px 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ── Practice card ── */
.practice-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0,0,0,.06);
  border: 2px solid transparent;
  transition: border-color .2s;
}
.practice-card.is-done { border-color: #67c23a; }

.practice-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.practice-weekday { font-size: 13px; color: #909399; }
.practice-title   { font-size: 20px; font-weight: 700; color: #1a1a2e; margin: 0 0 16px; }

.practice-instruction {
  background: #f8f9ff;
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 16px;
}
.instruction-text {
  font-family: inherit;
  font-size: 14px;
  line-height: 1.8;
  color: #4a4a6a;
  white-space: pre-wrap;
  margin: 0;
}

.practice-target {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #606266;
  margin-bottom: 14px;
}

.key-points { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.key-points-label { font-size: 13px; color: #909399; }
.kp-tag { border-radius: 12px !important; }

/* ── Recording panel ── */
.recording-panel {
  background: #fff;
  border-radius: 16px;
  padding: 32px 24px;
  box-shadow: 0 2px 12px rgba(0,0,0,.06);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}
.record-hint { font-size: 13px; color: #909399; text-align: center; margin: 0; }

.recording-active {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  width: 100%;
}

.rec-pulse {
  width: 20px; height: 20px;
  border-radius: 50%;
  background: #f56c6c;
  animation: pulse 1s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50%       { transform: scale(1.4); opacity: .7; }
}

.rec-timer {
  font-size: 48px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: #1a1a2e;
  line-height: 1;
}

.rec-target-bar {
  width: 100%;
  height: 8px;
  background: #e4e7ef;
  border-radius: 4px;
  overflow: hidden;
}
.rec-target-fill {
  height: 100%;
  background: #409eff;
  border-radius: 4px;
  transition: width .5s linear;
}
.rec-target-fill.overshoot { background: #f56c6c; }

.rec-target-label { font-size: 13px; color: #909399; }
.overshoot-text   { color: #f56c6c; font-weight: 600; }

.uploading-state {
  display: flex; flex-direction: column; align-items: center;
  gap: 12px; color: #606266; font-size: 14px;
}

/* ── Score panel ── */
.score-panel {
  width: 100%;
  display: flex; flex-direction: column; align-items: center; gap: 20px;
}

.score-circle {
  width: 100px; height: 100px;
  border-radius: 50%;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  border: 4px solid;
}
.score-circle.score-high { border-color: #67c23a; background: #f0f9eb; }
.score-circle.score-mid  { border-color: #e6a23c; background: #fdf6ec; }
.score-circle.score-low  { border-color: #f56c6c; background: #fef0f0; }

.score-num  { font-size: 32px; font-weight: 800; line-height: 1; }
.score-unit { font-size: 12px; color: #909399; }
.score-circle.score-high .score-num { color: #67c23a; }
.score-circle.score-mid  .score-num { color: #e6a23c; }
.score-circle.score-low  .score-num { color: #f56c6c; }

.score-dims { display: flex; gap: 12px; flex-wrap: wrap; justify-content: center; }
.dim-item {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; color: #606266;
  background: #f4f6fa; padding: 6px 12px; border-radius: 20px;
}
.dim-icon { font-size: 15px; }

.feedback-list { width: 100%; display: flex; flex-direction: column; gap: 8px; }
.feedback-item {
  background: #f8f9ff;
  border-left: 3px solid #409eff;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px; color: #4a4a6a; line-height: 1.6;
}

.streak-badge {
  display: flex; align-items: center; gap: 10px;
  background: #fff7e6; border: 1px solid #ffd591; border-radius: 20px;
  padding: 8px 20px; font-size: 15px; font-weight: 600; color: #ad6800;
}
.streak-badge.new-record {
  background: linear-gradient(135deg, #fff7e6, #fff0b3);
  border-color: #ffd666;
}
.new-record-badge {
  background: #fa8c16; color: #fff; font-size: 12px;
  padding: 2px 8px; border-radius: 10px;
}

.ref-answer { width: 100%; }
.ref-title  { font-size: 14px; font-weight: 600; color: #303133; }
.ref-content { font-size: 13px; color: #4a4a6a; line-height: 1.8; white-space: pre-wrap; padding: 4px 8px; }

.redo-btn { margin-top: 4px; width: 160px; }

/* ── History ── */
.history-strip {
  background: #fff; border-radius: 16px; padding: 20px;
  box-shadow: 0 2px 12px rgba(0,0,0,.06);
}
.history-title { font-size: 14px; font-weight: 600; color: #606266; margin: 0 0 14px; }
.history-list  { display: flex; gap: 8px; flex-wrap: wrap; }

.history-dot {
  display: flex; flex-direction: column; align-items: center; gap: 2px;
  width: 44px; padding: 8px 4px; border-radius: 10px;
}
.history-dot.score-high { background: #f0f9eb; }
.history-dot.score-mid  { background: #fdf6ec; }
.history-dot.score-low  { background: #fef0f0; }

.dot-date { font-size: 11px; color: #909399; }
.dot-score { font-size: 13px; font-weight: 700; }
.history-dot.score-high .dot-score { color: #67c23a; }
.history-dot.score-mid  .dot-score { color: #e6a23c; }
.history-dot.score-low  .dot-score { color: #f56c6c; }
</style>
