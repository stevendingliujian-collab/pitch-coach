<template>
  <div class="v2-page dp-page">
    <!-- Topbar -->
    <div class="v2-topbar">
      <span class="v2-topbar-title">每日微练习</span>
      <span class="topbar-breadcrumb">/ {{ weekdayLabel }} · {{ typeLabelStr }}</span>
      <div class="v2-topbar-flex" />
      <button class="btn-v2 btn-v2-ghost" @click="showHistory = !showHistory">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.8">
          <circle cx="7" cy="7" r="5.5"/><polyline points="7 4 7 7 9 9"/>
        </svg>
        历史记录
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="v2-content">
      <el-skeleton :rows="6" animated />
    </div>

    <!-- Main 2-col layout (shown when not loading) -->
    <div v-if="!loading && today" class="v2-content dp-layout">

      <!-- Upcoming pitch countdown banner (inside the layout) -->
      <div
        v-if="today.upcoming_task"
        class="countdown-banner"
        :class="{ 'countdown-urgent': today.upcoming_task.days_left <= 2 }"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8">
          <circle cx="8" cy="8" r="6.5"/>
          <polyline points="8 4.5 8 8 10 10"/>
        </svg>
        <span class="countdown-text">
          <template v-if="today.practice_type === 'bid_countdown'">
            🔥 述标倒计时练习已激活 — 距「{{ today.upcoming_task.name }}」还有
            <strong class="countdown-days">{{ today.upcoming_task.days_left }}</strong> 天
          </template>
          <template v-else>
            距「{{ today.upcoming_task.name }}」述标还有
            <strong class="countdown-days">{{ today.upcoming_task.days_left }}</strong> 天，保持每日练习！
          </template>
        </span>
        <router-link :to="`/projects/${today.upcoming_task.task_id}`" class="countdown-link">查看项目 →</router-link>
      </div>

      <!-- ── Left: Exercise card ── -->
      <div class="dp-main">
        <div class="dp-exercise-card v2-card">
          <!-- Card header: type badge + weekday + target -->
          <div class="ex-header">
            <div class="ex-tags">
              <span class="ex-type-badge" :class="`type-${today.practice_type}`">{{ typeLabel(today.practice_type) }}</span>
              <span class="ex-weekday">{{ weekdayLabel }}</span>
              <span v-if="today.status === 1 && recState !== 'scored'" class="ex-done-badge">✓ 今日已完成</span>
            </div>
            <div class="ex-target-pill">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.8">
                <circle cx="6" cy="6" r="4.5"/><polyline points="6 3.5 6 6 7.5 7.5"/>
              </svg>
              目标 {{ today.target_duration_sec }} 秒
            </div>
          </div>

          <h2 class="ex-title">{{ today.title }}</h2>

          <div class="ex-instruction">
            <pre class="ex-instruction-text">{{ today.instruction }}</pre>
          </div>

          <!-- Key points tags -->
          <div v-if="today.key_points.length" class="ex-keypoints">
            <span class="ex-kp-label">评分关键点</span>
            <div class="ex-kp-tags">
              <span v-for="kp in today.key_points" :key="kp" class="ex-kp-tag">{{ kp }}</span>
            </div>
          </div>

          <!-- Scoring meta footer -->
          <div class="ex-meta-footer">
            <span class="ex-meta-item">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.8">
                <polyline points="2 9 5 6 8 8 10.5 3"/>
              </svg>
              评分 3 维度
            </span>
            <span class="ex-meta-item">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.8">
                <polygon points="6 1 7.5 4.5 11.5 4.8 8.5 7.5 9.5 11.5 6 9.3 2.5 11.5 3.5 7.5 0.5 4.8 4.5 4.5"/>
              </svg>
              满分 100
            </span>
          </div>
        </div>

        <!-- ── Recording panel ── -->
        <div class="dp-record-panel v2-card">

          <!-- IDLE -->
          <template v-if="recState === 'idle'">
            <button
              class="record-btn"
              :class="{ 'record-btn-redo': today.status === 1 }"
              :disabled="starting"
              @click="startRecording"
            >
              <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="8" y="2" width="6" height="12" rx="3"/>
                <path d="M4 11c0 3.866 3.134 7 7 7s7-3.134 7-7"/>
                <line x1="11" y1="18" x2="11" y2="21"/><line x1="7" y1="21" x2="15" y2="21"/>
              </svg>
              {{ today.status === 1 ? '再练一次' : '开始录音' }}
            </button>
            <p class="record-hint">点击后自动计时 · AI 完成后即时评分</p>
          </template>

          <!-- RECORDING -->
          <template v-else-if="recState === 'recording'">
            <div class="rec-active">
              <div class="rec-header">
                <div class="rec-dot-blink" />
                <span class="rec-label">正在录音</span>
              </div>
              <div class="rec-timer">{{ formatTime(elapsed) }}</div>
              <div class="rec-progress-track">
                <div
                  class="rec-progress-fill"
                  :style="{ width: Math.min((elapsed / today.target_duration_sec) * 100, 100) + '%' }"
                  :class="{ overshoot: elapsed > today.target_duration_sec }"
                />
              </div>
              <div class="rec-progress-label">
                目标 {{ today.target_duration_sec }}s
                <span v-if="elapsed > today.target_duration_sec" class="rec-overshoot">
                  已超 {{ elapsed - today.target_duration_sec }}s
                </span>
              </div>
              <button class="stop-btn" :disabled="stopping" @click="stopAndScore">
                <svg width="16" height="16" viewBox="0 0 16 16"><rect x="3" y="3" width="10" height="10" rx="2" fill="currentColor"/></svg>
                完成录音
              </button>
            </div>
          </template>

          <!-- UPLOADING -->
          <template v-else-if="recState === 'uploading'">
            <div class="uploading-state">
              <div class="upload-spinner" />
              <div class="upload-text">上传并评分中…</div>
              <div class="upload-bar-track">
                <div class="upload-bar-fill" :style="{ width: uploadPct + '%' }" />
              </div>
              <div class="upload-pct">{{ uploadPct }}%</div>
            </div>
          </template>

          <!-- SCORED -->
          <template v-else-if="recState === 'scored' && scoreResult">
            <div class="score-reveal">
              <div class="score-ring" :class="scoreClass(scoreResult.total_score)">
                <svg width="88" height="88" viewBox="0 0 88 88">
                  <circle cx="44" cy="44" r="36" fill="none" stroke="#E5E7EB" stroke-width="5"/>
                  <circle
                    cx="44" cy="44" r="36"
                    fill="none"
                    :stroke="scoreRingColor(scoreResult.total_score)"
                    stroke-width="5"
                    stroke-linecap="round"
                    :stroke-dasharray="`${2 * Math.PI * 36}`"
                    :stroke-dashoffset="`${2 * Math.PI * 36 * (1 - scoreResult.total_score / 100)}`"
                    transform="rotate(-90 44 44)"
                    style="transition: stroke-dashoffset 0.8s ease;"
                  />
                </svg>
                <div class="score-ring-inner">
                  <span class="score-big">{{ scoreResult.total_score.toFixed(0) }}</span>
                  <span class="score-unit">分</span>
                </div>
              </div>

              <div class="score-dims">
                <div class="score-dim">
                  <span class="dim-label">时长</span>
                  <span class="dim-val">{{ scoreResult.timing_sec }}s / {{ today.target_duration_sec }}s</span>
                </div>
                <div class="score-dim">
                  <span class="dim-label">填充词</span>
                  <span class="dim-val">{{ scoreResult.filler_count }} 次</span>
                </div>
                <div class="score-dim">
                  <span class="dim-label">关键点</span>
                  <span class="dim-val">{{ Math.round(scoreResult.keyword_hit_rate * 100) }}%</span>
                </div>
              </div>

              <div v-if="scoreResult.feedback?.length" class="score-feedback">
                <div v-for="(f, i) in scoreResult.feedback" :key="i" class="feedback-line">{{ f }}</div>
              </div>

              <div v-if="scoreResult.current_streak > 0" class="streak-celebrate">
                🔥 连续练习 {{ scoreResult.current_streak }} 天
                <span v-if="scoreResult.is_new_record" class="new-record">新纪录！</span>
              </div>

              <el-collapse v-if="scoreResult.reference_answer" class="ref-collapse">
                <el-collapse-item name="ref">
                  <template #title><span class="ref-title">📖 参考答案</span></template>
                  <div class="ref-content">{{ scoreResult.reference_answer }}</div>
                </el-collapse-item>
              </el-collapse>

              <button class="btn-v2 btn-v2-ghost" style="width:100%;justify-content:center;margin-top:4px" @click="resetForRedo">
                再练一次
              </button>
            </div>
          </template>

        </div>
      </div>

      <!-- ── Right: Streak + Plan + History ── -->
      <div class="dp-aside">

        <!-- Streak card -->
        <div class="aside-card v2-card">
          <div class="streak-top">
            <div class="streak-num">{{ streakInfo?.current_streak ?? 0 }}</div>
            <span class="streak-fire">🔥</span>
          </div>
          <div class="streak-sub">天连续练习</div>
          <!-- Week dots -->
          <div class="week-dots">
            <span
              v-for="(d, i) in weekDots"
              :key="i"
              class="week-dot"
              :class="{ done: d.done, today: d.isToday }"
              :title="d.label"
            />
          </div>
          <div class="week-labels">
            <span v-for="l in ['一','二','三','四','五','六','日']" :key="l">{{ l }}</span>
          </div>
        </div>

        <!-- Weekly plan -->
        <div class="aside-card v2-card">
          <div class="aside-card-title">本周练习计划</div>
          <div class="weekly-plan">
            <div
              v-for="(item, i) in weeklyPlan"
              :key="i"
              class="weekly-item"
              :class="{ active: item.isToday }"
            >
              <span class="weekly-dot" :class="`dot-${item.type}`" />
              <span class="weekly-name">{{ item.name }}</span>
              <span v-if="item.isToday" class="weekly-today-badge">← 今天</span>
            </div>
          </div>
        </div>

        <!-- History score bars -->
        <div v-if="history.length" class="aside-card v2-card">
          <div class="aside-card-title">近 {{ history.length }} 次得分</div>
          <div class="history-bars">
            <div
              v-for="(item, i) in history.slice().reverse()"
              :key="i"
              class="history-bar-wrap"
              :title="`${item.practice_date} · ${item.total_score?.toFixed(0) ?? '--'}分`"
            >
              <div
                class="history-bar"
                :style="{ height: (item.total_score ?? 0) * 0.52 + 'px' }"
                :class="scoreClass(item.total_score ?? 0)"
              />
            </div>
          </div>
          <div class="history-stats">
            平均 <strong>{{ avgScore }}</strong> 分 · 最高 <strong>{{ maxScore }}</strong> 分
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  dailyPracticeApi,
  type TodayPractice,
  type PracticeScoreResponse,
  type PracticeHistoryItem,
  type StreakInfo,
} from '@/api/dailyPractice'

const router = useRouter()

// ─── state ─────────────────────────────────────────────────────────
const loading     = ref(true)
const today       = ref<TodayPractice | null>(null)
const streakInfo  = ref<StreakInfo | null>(null)
const history     = ref<PracticeHistoryItem[]>([])
const scoreResult = ref<PracticeScoreResponse | null>(null)
const showHistory = ref(false)

type RecState = 'idle' | 'recording' | 'uploading' | 'scored'
const recState  = ref<RecState>('idle')
const starting  = ref(false)
const stopping  = ref(false)
const uploadPct = ref(0)
const elapsed   = ref(0)

let mediaRecorder: MediaRecorder | null = null
let audioChunks: Blob[] = []
let currentLogId = 0
let currentObjectKey = ''
let currentUploadUrl = ''
let timerHandle: ReturnType<typeof setInterval> | null = null

// ─── lifecycle ────────────────────────────────────────────────────
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

// ─── computed ─────────────────────────────────────────────────────
const weekdayLabel = computed(() => {
  const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
  const d = new Date().getDay()
  return days[d === 0 ? 6 : d - 1]
})

const typeLabelStr = computed(() => today.value ? typeLabel(today.value.practice_type) : '')

const weeklyPlan = computed(() => {
  const dow = new Date().getDay()
  const todayIdx = dow === 0 ? 6 : dow - 1
  return [
    { name: '周一 · 口播开场', type: 'intro', isToday: todayIdx === 0 },
    { name: '周二 · 案例讲解', type: 'case',  isToday: todayIdx === 1 },
    { name: '周三 · 技术术语', type: 'term',  isToday: todayIdx === 2 },
    { name: '周四 · 质疑回应', type: 'qa',    isToday: todayIdx === 3 },
    { name: '周五 · 竞品对比', type: 'comp',  isToday: todayIdx === 4 },
    { name: '周末 · 综合复习', type: 'rev',   isToday: todayIdx >= 5 },
  ]
})

const weekDots = computed(() => {
  const dow = new Date().getDay()
  const todayIdx = dow === 0 ? 6 : dow - 1
  return Array.from({ length: 7 }, (_, i) => ({
    label: ['一','二','三','四','五','六','日'][i],
    done: i < todayIdx || (i === todayIdx && today.value?.status === 1),
    isToday: i === todayIdx,
  }))
})

const avgScore = computed(() => {
  const scores = history.value.filter(h => h.total_score !== null).map(h => h.total_score!)
  if (!scores.length) return 0
  return Math.round(scores.reduce((s, v) => s + v, 0) / scores.length)
})
const maxScore = computed(() => {
  const scores = history.value.filter(h => h.total_score !== null).map(h => h.total_score!)
  return scores.length ? Math.round(Math.max(...scores)) : 0
})

// ─── recording methods ────────────────────────────────────────────
async function startRecording() {
  if (!today.value) return
  starting.value = true
  try {
    const res = await dailyPracticeApi.start(today.value.item_id)
    currentLogId     = res.data.log_id
    currentObjectKey = res.data.object_key
    currentUploadUrl = res.data.upload_url

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' })
    audioChunks = []
    mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data) }
    mediaRecorder.start(200)

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
    await new Promise<void>((resolve) => {
      mediaRecorder!.onstop = () => resolve()
      mediaRecorder!.stop()
      mediaRecorder!.stream.getTracks().forEach(t => t.stop())
    })

    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' })
    recState.value = 'uploading'
    uploadPct.value = 0

    await dailyPracticeApi.uploadAudio(currentUploadUrl, audioBlob, (pct) => { uploadPct.value = Math.min(pct, 90) })
    uploadPct.value = 95

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
  return ({ intro: '口播开场', case: '案例讲解', term: '术语解释', qa: '质疑回应', competitive: '竞品话术', review: '综合复习', bid_countdown: '述标冲刺' } as Record<string, string>)[type] ?? type
}

function scoreClass(score: number) {
  if (score >= 85) return 'score-high'
  if (score >= 70) return 'score-mid'
  return 'score-low'
}

function scoreRingColor(score: number) {
  if (score >= 85) return '#22C55E'
  if (score >= 70) return '#F59E0B'
  return '#EF4444'
}
</script>

<style scoped>
.dp-page { background: var(--bg-content); }

/* Countdown banner */
.countdown-banner {
  display: flex; align-items: center; gap: 10px;
  background: linear-gradient(135deg, #FEF3C7, #FDE68A);
  border: 1px solid #F59E0B;
  border-radius: 10px;
  padding: 10px 16px; font-size: 13px; color: #78350F;
  margin-bottom: 16px;
}
.countdown-banner.countdown-urgent {
  background: linear-gradient(135deg, #FEE2E2, #FECACA);
  border-color: #EF4444;
  color: #7F1D1D;
}
.countdown-banner.countdown-urgent .countdown-days { color: #DC2626; }
.countdown-days { font-size: 16px; font-weight: 800; color: #B45309; margin: 0 3px; }
.countdown-link {
  margin-left: auto; font-size: 12px; font-weight: 600;
  color: #92400E; text-decoration: none; white-space: nowrap;
}
.countdown-link:hover { text-decoration: underline; }

.topbar-breadcrumb { font-size: 13px; color: var(--t-faint); margin-left: 4px; }

/* 2-col layout */
.dp-layout {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 20px;
  align-items: start;
}
/* Countdown banner spans both columns */
.countdown-banner { grid-column: 1 / -1; }
@media (max-width: 860px) { .dp-layout { grid-template-columns: 1fr; } }

/* Exercise card */
.dp-exercise-card { padding: 24px; margin-bottom: 16px; }
.ex-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px; }
.ex-tags   { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

.ex-type-badge {
  padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 700;
}
.type-intro { background: rgba(99,102,241,0.1); color: #6366F1; }
.type-case  { background: rgba(34,197,94,0.1);  color: #16A34A; }
.type-term  { background: rgba(6,182,212,0.1);   color: #0891B2; }
.type-qa    { background: rgba(245,158,11,0.1);  color: #D97706; }
.type-competitive { background: rgba(239,68,68,0.1); color: #DC2626; }
.type-review { background: rgba(107,114,128,0.1); color: #4B5563; }
.type-bid_countdown { background: rgba(239,68,68,0.15); color: #EF4444; font-weight: 800; }

.ex-weekday { font-size: 12px; color: var(--t-faint); }
.ex-done-badge { font-size: 11px; font-weight: 600; color: var(--green); background: rgba(34,197,94,0.1); padding: 2px 8px; border-radius: 10px; }
.ex-target-pill {
  display: flex; align-items: center; gap: 4px;
  font-size: 12px; font-weight: 600; color: var(--t-muted);
  background: var(--bg-content); border: 1px solid var(--border);
  padding: 3px 10px; border-radius: 20px; flex-shrink: 0;
}

.ex-title { font-size: 20px; font-weight: 800; color: var(--t-primary); margin-bottom: 14px; line-height: 1.3; }

.ex-instruction {
  background: var(--bg-content); border-radius: var(--radius-md);
  padding: 14px 16px; margin-bottom: 16px;
}
.ex-instruction-text {
  font-family: inherit; font-size: 13.5px; line-height: 1.85;
  color: var(--t-secondary); white-space: pre-wrap; margin: 0;
}

.ex-keypoints { margin-bottom: 14px; }
.ex-kp-label { font-size: 12px; font-weight: 600; color: var(--t-muted); margin-bottom: 6px; display: block; }
.ex-kp-tags  { display: flex; flex-wrap: wrap; gap: 6px; }
.ex-kp-tag   {
  padding: 4px 12px; border-radius: 20px; font-size: 12px;
  background: var(--accent-dim); color: var(--accent); border: 1px solid var(--accent-light); font-weight: 600;
}

.ex-meta-footer {
  display: flex; gap: 16px; padding-top: 14px; border-top: 1px solid var(--border-light);
}
.ex-meta-item {
  display: flex; align-items: center; gap: 4px;
  font-size: 12px; color: var(--t-faint);
}

/* Record panel */
.dp-record-panel { padding: 28px 24px; display: flex; flex-direction: column; align-items: center; gap: 12px; }

.record-btn {
  display: flex; align-items: center; gap: 10px;
  padding: 14px 32px; border-radius: 40px;
  background: var(--accent); color: #fff;
  font-size: 15px; font-weight: 700; border: none; cursor: pointer;
  transition: all 0.2s; font-family: inherit;
  box-shadow: 0 4px 14px rgba(99,102,241,0.35);
}
.record-btn:hover { background: #5457e0; transform: translateY(-1px); box-shadow: 0 6px 20px rgba(99,102,241,0.45); }
.record-btn:disabled { opacity: 0.65; cursor: not-allowed; transform: none; }
.record-btn-redo { background: var(--bg-content); color: var(--t-secondary); border: 1.5px solid var(--border); box-shadow: none; }
.record-btn-redo:hover { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }

.record-hint { font-size: 12px; color: var(--t-faint); text-align: center; }

/* Recording active */
.rec-active { width: 100%; display: flex; flex-direction: column; align-items: center; gap: 10px; }
.rec-header { display: flex; align-items: center; gap: 8px; }
.rec-dot-blink {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--red); box-shadow: 0 0 8px rgba(239,68,68,0.8);
  animation: blink 1.2s ease-in-out infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.2} }
.rec-label  { font-size: 12px; font-weight: 700; color: var(--t-muted); letter-spacing: 1px; text-transform: uppercase; }
.rec-timer  { font-size: 56px; font-weight: 900; color: var(--t-primary); letter-spacing: -2px; line-height: 1; font-variant-numeric: tabular-nums; }
.rec-progress-track { width: 100%; height: 4px; background: var(--border-light); border-radius: 2px; overflow: hidden; }
.rec-progress-fill  { height: 100%; border-radius: 2px; background: var(--accent); transition: width 0.5s; }
.rec-progress-fill.overshoot { background: var(--orange); }
.rec-progress-label { font-size: 12px; color: var(--t-faint); }
.rec-overshoot { color: var(--orange); font-weight: 600; margin-left: 6px; }
.stop-btn {
  display: flex; align-items: center; gap: 8px;
  padding: 11px 28px; border-radius: 30px; font-size: 14px; font-weight: 700;
  background: var(--red); color: #fff; border: none; cursor: pointer;
  transition: all 0.15s; font-family: inherit; margin-top: 6px;
}
.stop-btn:hover { background: #dc2626; }
.stop-btn:disabled { opacity: 0.65; cursor: not-allowed; }

/* Uploading */
.uploading-state { display: flex; flex-direction: column; align-items: center; gap: 10px; width: 100%; }
.upload-spinner {
  width: 36px; height: 36px; border-radius: 50%;
  border: 3px solid var(--border-light); border-top-color: var(--accent);
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.upload-text { font-size: 13px; color: var(--t-muted); font-weight: 500; }
.upload-bar-track { width: 100%; height: 4px; background: var(--border-light); border-radius: 2px; overflow: hidden; }
.upload-bar-fill  { height: 100%; background: var(--accent); transition: width 0.3s; }
.upload-pct { font-size: 12px; color: var(--t-faint); }

/* Score reveal */
.score-reveal { width: 100%; display: flex; flex-direction: column; align-items: center; gap: 12px; }
.score-ring   { position: relative; width: 88px; height: 88px; }
.score-ring-inner {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
}
.score-big  { font-size: 26px; font-weight: 900; color: var(--t-primary); line-height: 1; }
.score-unit { font-size: 11px; color: var(--t-muted); }

.score-dims { display: flex; gap: 16px; }
.score-dim  { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.dim-label  { font-size: 11px; color: var(--t-faint); }
.dim-val    { font-size: 13px; font-weight: 700; color: var(--t-primary); }

.score-feedback { width: 100%; background: var(--bg-content); border-radius: var(--radius-md); padding: 10px 14px; }
.feedback-line  { font-size: 13px; color: var(--t-secondary); line-height: 1.7; }

.streak-celebrate {
  font-size: 14px; font-weight: 700; color: var(--orange);
  background: rgba(249,115,22,0.08); padding: 7px 16px; border-radius: 20px;
}
.new-record { font-size: 11px; color: var(--green); font-weight: 700; margin-left: 8px; }

.ref-collapse { width: 100%; }
.ref-title   { font-size: 13px; font-weight: 600; color: var(--t-muted); }
.ref-content { font-size: 13px; color: var(--t-secondary); line-height: 1.7; padding: 8px 0; }

/* Aside cards */
.dp-aside { display: flex; flex-direction: column; gap: 14px; }
.aside-card { padding: 18px; }
.aside-card-title { font-size: 13px; font-weight: 700; color: var(--t-primary); margin-bottom: 12px; }

/* Streak */
.streak-top { display: flex; align-items: flex-end; gap: 6px; margin-bottom: 2px; }
.streak-num { font-size: 40px; font-weight: 900; color: var(--t-primary); line-height: 1; }
.streak-fire { font-size: 28px; }
.streak-sub { font-size: 12px; color: var(--t-faint); margin-bottom: 14px; }

.week-dots  { display: flex; gap: 6px; margin-bottom: 4px; }
.week-dot   {
  flex: 1; height: 8px; border-radius: 4px;
  background: var(--border-light); transition: background 0.2s;
}
.week-dot.done  { background: var(--accent); }
.week-dot.today { background: var(--orange); }
.week-labels { display: flex; gap: 6px; }
.week-labels span { flex: 1; text-align: center; font-size: 10px; color: var(--t-faint); }

/* Weekly plan */
.weekly-plan { display: flex; flex-direction: column; gap: 8px; }
.weekly-item { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--t-muted); }
.weekly-item.active { color: var(--t-primary); font-weight: 600; }
.weekly-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.dot-intro { background: var(--accent); }
.dot-case  { background: var(--green); }
.dot-term  { background: var(--cyan); }
.dot-qa    { background: var(--amber); }
.dot-comp  { background: var(--red); }
.dot-rev   { background: var(--orange); }
.weekly-today-badge { margin-left: auto; font-size: 10px; color: var(--accent); font-weight: 700; }

/* History bars */
.history-bars { display: flex; align-items: flex-end; gap: 5px; height: 56px; margin-bottom: 8px; }
.history-bar-wrap { flex: 1; display: flex; align-items: flex-end; justify-content: center; }
.history-bar { width: 100%; border-radius: 3px 3px 0 0; min-height: 4px; transition: height 0.4s; }
.history-bar.score-high { background: var(--green); }
.history-bar.score-mid  { background: var(--amber); }
.history-bar.score-low  { background: var(--red); }
.history-stats { font-size: 12px; color: var(--t-faint); text-align: center; }
.history-stats strong { color: var(--t-primary); }

/* ── Mobile responsive ───────────────────────────────────── */
@media (max-width: 600px) {
  .dp-view { padding: 16px; }
  .dp-header { flex-direction: column; align-items: flex-start; gap: 10px; }
  .dp-header-actions { width: 100%; }
  .rec-btn { width: 100%; justify-content: center; padding: 14px; font-size: 15px; border-radius: 12px; }
  .rec-btn svg { width: 22px; height: 22px; }
  .dp-exercise-card { padding: 16px; }
  .ex-header { flex-direction: column; align-items: flex-start; gap: 8px; }
  .score-display { font-size: 56px; }
  .feedback-grid { grid-template-columns: 1fr; }
}
</style>
