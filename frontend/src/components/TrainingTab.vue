<template>
  <div class="training-tab">

    <!-- ── Plan header ── -->
    <div v-if="plan" class="plan-header">
      <div class="plan-meta">
        <span class="meta-label">训练计划</span>
        <el-tag type="success" size="small">已创建</el-tag>
        <span v-if="plan.bid_date" class="bid-date">述标日期：{{ plan.bid_date }}</span>
      </div>
      <div class="schedule-strip">
        <div
          v-for="d in plan.schedule_dates ?? []"
          :key="d"
          class="schedule-dot"
          :class="{ past: d < today, today: d === today, future: d > today }"
          :title="d"
        >
          <span class="dot-label">{{ formatShortDate(d) }}</span>
        </div>
      </div>
    </div>

    <!-- ── No plan yet ── -->
    <div v-else class="empty-state">
      <el-empty description="尚未创建训练计划">
        <el-button type="primary" @click="initPlan" :loading="creating">开始训练计划</el-button>
      </el-empty>
    </div>

    <template v-if="plan">
      <!-- ── Mode + page selector ── -->
      <div class="mode-bar">
        <el-radio-group v-model="selectedMode" size="default">
          <el-radio-button value="follow">
            <el-icon style="margin-right:4px"><Headset /></el-icon>跟读模式
          </el-radio-button>
          <el-radio-button value="recite">
            <el-icon style="margin-right:4px"><Microphone /></el-icon>背诵模式
          </el-radio-button>
        </el-radio-group>

        <div class="page-nav" style="margin-left:16px">
          <el-button
            :icon="ArrowLeft"
            :disabled="!hasPrevPage"
            @click="goPrevPage"
            size="default"
            title="上一页"
          />
          <el-select
            v-model="selectedPage"
            placeholder="选择页面"
            style="width:190px"
            @change="onPageChange"
          >
            <el-option
              v-for="p in pages"
              :key="p.page_number"
              :value="p.page_number"
              :label="`第 ${p.page_number} 页${p.page_title ? ' · ' + p.page_title : ''}`"
            />
          </el-select>
          <el-button
            :icon="ArrowRight"
            :disabled="!hasNextPage"
            @click="goNextPage"
            size="default"
            title="下一页"
          />
          <span class="page-counter">{{ currentPageIndex + 1 }} / {{ pages.length }}</span>
        </div>
      </div>

      <!-- ══════════════════════════════════════════════════════════
           MAIN LAYOUT: left = page view  |  right = practice
      ══════════════════════════════════════════════════════════════ -->
      <div class="main-layout">

        <!-- ────────── Left: page viewer ────────── -->
        <div class="page-viewer" v-if="currentPage">
          <!-- Large thumbnail -->
          <div class="slide-frame">
            <el-image
              v-if="currentPage.page_thumbnail_url"
              :src="currentPage.page_thumbnail_url"
              fit="contain"
              class="slide-img"
            />
            <div v-else class="slide-placeholder">
              <span class="slide-num">{{ currentPage.page_number }}</span>
            </div>
            <!-- Page badge -->
            <div class="slide-badge">
              第 {{ currentPage.page_number }} 页
              <el-tag
                v-if="currentPage.importance_level"
                :type="importanceType(currentPage.importance_level)"
                size="small"
                style="margin-left:6px"
              >{{ importanceLabel(currentPage.importance_level) }}</el-tag>
              <span v-if="currentPage.suggested_duration" class="slide-dur">
                ⏱ {{ currentPage.suggested_duration }}秒
              </span>
            </div>
          </div>

          <!-- Page title -->
          <div class="page-title-text" v-if="currentPage.page_title">
            {{ currentPage.page_title }}
          </div>

          <!-- Talking points -->
          <div class="points-section">
            <div class="points-label">
              {{ selectedMode === 'recite' ? '📌 记忆要点' : '📋 讲解要点' }}
            </div>
            <ul class="talking-points">
              <li
                v-for="(tp, i) in currentPage.talking_points ?? []"
                :key="i"
                :class="{ emphasis: tp.is_emphasis }"
              >
                <span v-if="tp.is_emphasis" class="star">★</span>
                {{ tp.point }}
              </li>
              <li v-if="!currentPage.talking_points?.length" class="empty-point">暂无要点</li>
            </ul>
          </div>

          <!-- Transition hint -->
          <div v-if="currentPage.transition_hint" class="transition-hint">
            <el-icon><ArrowRight /></el-icon>
            过渡语参考：{{ currentPage.transition_hint }}
          </div>
        </div>

        <!-- ────────── Right: practice ────────── -->
        <div class="practice-col">

          <!-- Demo player (follow mode) -->
          <div v-if="selectedMode === 'follow'" class="panel demo-panel">
            <div class="panel-title">
              <el-icon><VideoPlay /></el-icon> 示范讲解
              <el-tag v-if="currentPageAudio" type="success" size="small" style="margin-left:8px">
                {{ formatSec(currentPageAudio.duration_sec) }}
              </el-tag>
            </div>

            <template v-if="currentPageAudio">
              <audio
                ref="demoAudioEl"
                :src="currentPageAudio.audio_url"
                controls
                class="demo-audio"
                preload="metadata"
              />
              <el-collapse v-model="showScript" style="margin-top:10px">
                <el-collapse-item title="查看示范脚本" name="script">
                  <p class="script-text">{{ currentPageAudio.script }}</p>
                  <el-tag type="info" size="small" style="margin-top:6px">
                    语调：{{ currentPageAudio.tone }}
                  </el-tag>
                </el-collapse-item>
              </el-collapse>
            </template>
            <el-alert v-else-if="narrationLoading" type="info" :closable="false" show-icon>
              加载示范讲解中…
            </el-alert>
            <el-alert v-else-if="!narration" type="info" :closable="false" show-icon>
              尚未生成 AI 示范讲解，可在「AI 示范讲解」标签页生成后回来跟读。
            </el-alert>
            <el-alert v-else-if="narration.status !== 4" type="warning" :closable="false" show-icon>
              示范讲解生成中（{{ narrationStatusLabel }}），完成后可跟读。
            </el-alert>
            <el-alert v-else type="info" :closable="false" show-icon>
              当前页面暂无示范音频，可先参考要点讲解。
            </el-alert>
          </div>

          <!-- Recite mode tip -->
          <el-alert
            v-if="selectedMode === 'recite'"
            type="warning"
            :closable="false"
            show-icon
          >
            <strong>背诵模式：</strong>不看稿件，凭记忆完整讲解本页内容，系统将评估要点覆盖率、顺序和流畅度。
          </el-alert>

          <!-- Recording area -->
          <div class="panel record-panel">
            <div class="panel-title">
              <el-icon><Microphone /></el-icon>
              {{ selectedMode === 'follow' ? '跟读录音' : '背诵录音' }}
            </div>

            <div class="record-body">
              <div class="timer" v-if="recording">
                <el-icon class="pulse"><Microphone /></el-icon>
                {{ formatDuration(elapsed) }}
              </div>
              <div class="record-buttons">
                <el-button
                  v-if="!recording && !sessionResult"
                  type="primary" :icon="Microphone" size="large" round
                  @click="startRecording"
                >开始录音</el-button>
                <el-button
                  v-if="recording"
                  type="danger" size="large" round
                  @click="stopRecording"
                >停止录音</el-button>
                <el-button v-if="sessionResult" size="large" round @click="resetSession">
                  再练一次
                </el-button>
              </div>
              <div v-if="showTranscriptInput" class="transcript-input">
                <p class="hint">讲解转录（暂时请手动输入，用于评分）：</p>
                <el-input v-model="manualTranscript" type="textarea" :rows="4"
                  placeholder="在此输入您刚才的讲解内容…" />
                <el-button type="primary" style="margin-top:8px" :loading="scoring"
                  @click="submitForScoring">提交评分</el-button>
              </div>
            </div>
          </div>

          <!-- Score card -->
          <transition name="fade">
            <div v-if="sessionResult" class="score-card">
              <div class="score-total">
                <el-progress
                  type="circle"
                  :percentage="sessionResult.total_score ?? 0"
                  :color="scoreColor(sessionResult.total_score ?? 0)"
                  :stroke-width="12" :width="100"
                />
                <div class="score-label">综合得分</div>
              </div>
              <div class="score-dims">
                <div v-for="(val, key) in sessionResult.dimension_scores ?? {}" :key="key" class="dim-item">
                  <div class="dim-name">{{ dimLabel(key) }}</div>
                  <el-progress :percentage="val" :color="scoreColor(val)" :stroke-width="8" />
                </div>
              </div>
              <div class="feedback-list" v-if="sessionResult.feedback?.length">
                <div class="feedback-title">改进建议</div>
                <ul>
                  <li v-for="(tip, i) in sessionResult.feedback" :key="i">{{ tip }}</li>
                </ul>
              </div>
              <div class="history-strip" v-if="sessionsForPage.length > 1">
                <span class="history-label">本页历史：</span>
                <el-tag
                  v-for="s in sessionsForPage.slice(0, 6)" :key="s.id"
                  :type="scoreTagType(s.total_score ?? 0)" size="small" style="margin-right:4px"
                >{{ s.total_score?.toFixed(0) }} 分</el-tag>
              </div>
            </div>
          </transition>
        </div>
      </div>

      <!-- History table -->
      <div class="history-section" v-if="allSessions.length">
        <div class="section-title">练习记录</div>
        <el-table :data="allSessions" size="small">
          <el-table-column label="日期" prop="practice_date" width="100" />
          <el-table-column label="模式" width="70">
            <template #default="{ row }">{{ row.mode === 'follow' ? '跟读' : '背诵' }}</template>
          </el-table-column>
          <el-table-column label="页" prop="page_number" width="50" align="center" />
          <el-table-column label="得分" width="80" align="center">
            <template #default="{ row }">
              <el-tag :type="scoreTagType(row.total_score ?? 0)" size="small">
                {{ row.total_score?.toFixed(0) ?? '—' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="主要反馈">
            <template #default="{ row }">{{ row.feedback?.[0] ?? '—' }}</template>
          </el-table-column>
        </el-table>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Microphone, Headset, VideoPlay, ArrowRight, ArrowLeft } from '@element-plus/icons-vue'
import { trainingApi, type TrainingPlan, type TrainingSession } from '@/api/training'
import { narrationApi, type DemoNarration } from '@/api/narration'
import type { PlanPage } from '@/api/pitchPlan'

const props = defineProps<{
  taskId: number
  planId: number | null
  pages: PlanPage[]
}>()

const plan        = ref<TrainingPlan | null>(null)
const creating    = ref(false)
const selectedMode = ref<'follow' | 'recite'>('follow')
const selectedPage = ref<number>(1)

const narration        = ref<DemoNarration | null>(null)
const narrationLoading = ref(false)
const showScript       = ref<string[]>([])
const demoAudioEl      = ref<HTMLAudioElement | null>(null)

const recording           = ref(false)
const elapsed             = ref(0)
let   elapsedTimer: ReturnType<typeof setInterval> | null = null
const showTranscriptInput = ref(false)
const manualTranscript    = ref('')
const scoring             = ref(false)
const sessionResult       = ref<TrainingSession | null>(null)
const allSessions         = ref<TrainingSession[]>([])
const today = new Date().toISOString().slice(0, 10)

const currentPage = computed(
  () => props.pages.find(p => p.page_number === selectedPage.value) ?? null
)
const currentPageIndex = computed(
  () => props.pages.findIndex(p => p.page_number === selectedPage.value)
)
const hasPrevPage = computed(() => currentPageIndex.value > 0)
const hasNextPage = computed(() => currentPageIndex.value < props.pages.length - 1)

function goPrevPage() {
  if (!hasPrevPage.value) return
  selectedPage.value = props.pages[currentPageIndex.value - 1].page_number
  onPageChange()
}
function goNextPage() {
  if (!hasNextPage.value) return
  selectedPage.value = props.pages[currentPageIndex.value + 1].page_number
  onPageChange()
}
const currentPageAudio = computed(() =>
  narration.value?.status === 4 && narration.value.page_audios
    ? (narration.value.page_audios.find(pa => pa.page_number === selectedPage.value) ?? null)
    : null
)
const narrationStatusLabel = computed(() =>
  ({0:'等待中',1:'生成脚本',2:'合成音频',3:'合并中',4:'就绪',5:'失败'} as Record<number,string>)
    [narration.value?.status ?? -1] ?? ''
)
const sessionsForPage = computed(() =>
  allSessions.value.filter(s => s.page_number === selectedPage.value && s.mode === selectedMode.value)
)

onMounted(async () => {
  if (props.pages.length) selectedPage.value = props.pages[0].page_number
  await Promise.all([loadPlan(), loadNarration()])
})
watch(() => props.planId, () => Promise.all([loadPlan(), loadNarration()]))

function onPageChange() {
  demoAudioEl.value?.pause()
  showScript.value = []
  resetSession()
}

async function loadPlan() {
  try {
    const res = await trainingApi.listPlans(props.taskId)
    plan.value = res.data[0] ?? null
    if (plan.value) await loadSessions()
  } catch { /* no plan */ }
}
async function initPlan() {
  creating.value = true
  try {
    const res = await trainingApi.createOrGetPlan(props.taskId, props.planId ?? undefined)
    plan.value = res.data
    ElMessage.success('训练计划已创建，按照艾宾浩斯复习曲线安排练习日期')
    await loadSessions()
  } catch { ElMessage.error('创建训练计划失败') }
  finally { creating.value = false }
}
async function loadSessions() {
  if (!plan.value) return
  try {
    const res = await trainingApi.listSessions({ plan_id: plan.value.id })
    allSessions.value = res.data
  } catch { /* ignore */ }
}
async function loadNarration() {
  if (!props.planId) return
  narrationLoading.value = true
  try {
    const res = await narrationApi.getLatest(props.planId)
    narration.value = res.data
  } catch { narration.value = null }
  finally { narrationLoading.value = false }
}

function startRecording() {
  recording.value = true; elapsed.value = 0
  showTranscriptInput.value = false; sessionResult.value = null
  elapsedTimer = setInterval(() => elapsed.value++, 1000)
}
function stopRecording() {
  recording.value = false
  if (elapsedTimer) clearInterval(elapsedTimer)
  showTranscriptInput.value = true
}
function resetSession() {
  sessionResult.value = null; showTranscriptInput.value = false
  manualTranscript.value = ''; elapsed.value = 0
}
async function submitForScoring() {
  if (!manualTranscript.value.trim()) { ElMessage.warning('请输入讲解内容后再提交'); return }
  if (!plan.value) return
  scoring.value = true
  try {
    const res = await trainingApi.submitSession({
      plan_id: plan.value.id, mode: selectedMode.value,
      page_number: selectedPage.value, transcript: manualTranscript.value,
      duration_sec: elapsed.value || 60,
    })
    sessionResult.value = res.data; showTranscriptInput.value = false
    await loadSessions()
  } catch { ElMessage.error('评分提交失败') }
  finally { scoring.value = false }
}

const formatShortDate = (iso: string) => { const d = new Date(iso); return `${d.getMonth()+1}/${d.getDate()}` }
const formatDuration  = (s: number) => `${String(Math.floor(s/60)).padStart(2,'0')}:${String(s%60).padStart(2,'0')}`
const formatSec       = (s: number) => { const m=Math.floor(s/60),r=Math.round(s%60); return m>0?`${m}分${r}秒`:`${r}秒` }
const scoreColor      = (s: number) => s>=85?'#67c23a':s>=70?'#e6a23c':'#f56c6c'
const scoreTagType    = (s: number): ''|'success'|'warning'|'danger' => s>=85?'success':s>=70?'warning':'danger'
const importanceLabel = (l: number) => (['','普通','重要','核心'] as const)[l] ?? ''
const importanceType  = (l: number): ''|'warning'|'danger' => l===3?'danger':l===2?'warning':''
const DIM_LABELS: Record<string,string> = {
  content_alignment:'内容贴合度', rate_match:'语速匹配度', emphasis_hits:'重音命中率',
  coverage_rate:'要点覆盖率', order_accuracy:'顺序准确性', naturalness:'表达自然度',
}
const dimLabel = (k: string) => DIM_LABELS[k] ?? k
</script>

<style scoped>
.training-tab { padding: 20px 24px; display: flex; flex-direction: column; gap: 16px; }

/* Plan header */
.plan-header { background:#f5f7fa; border-radius:8px; padding:12px 16px; }
.plan-meta   { display:flex; align-items:center; gap:10px; margin-bottom:10px; }
.meta-label  { font-weight:600; font-size:14px; }
.bid-date    { margin-left:auto; font-size:12px; color:#909399; }
.schedule-strip { display:flex; gap:8px; flex-wrap:wrap; }
.schedule-dot {
  display:flex; flex-direction:column; align-items:center;
  width:44px; padding:4px; border-radius:6px; font-size:11px;
}
.schedule-dot.past   { background:#e4e7ed; color:#c0c4cc; }
.schedule-dot.today  { background:#409eff; color:#fff; font-weight:700; }
.schedule-dot.future { background:#ecf5ff; color:#409eff; border:1px solid #b3d8ff; }
.dot-label { font-size:11px; }
.empty-state { text-align:center; padding:40px 0; }

/* Mode bar */
.mode-bar { display:flex; align-items:center; }

/* Page nav: prev ▸ select ▸ next */
.page-nav {
  display: flex;
  align-items: center;
  gap: 6px;
}
.page-counter {
  font-size: 13px;
  color: #909399;
  white-space: nowrap;
  min-width: 48px;
}

/* ═══════════════════════════════════════════
   Main layout: 60% page view | 40% practice
═══════════════════════════════════════════ */
.main-layout {
  display: grid;
  grid-template-columns: 3fr 2fr;
  gap: 20px;
  align-items: start;
}

/* ── Left: page viewer ── */
.page-viewer {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* Slide frame: big, 16:9-ish */
.slide-frame {
  position: relative;
  width: 100%;
  background: #1e1e2e;
  border-radius: 10px;
  overflow: hidden;
  /* 16:9 aspect ratio */
  aspect-ratio: 16 / 9;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 20px rgba(0,0,0,.18);
}
.slide-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}
.slide-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.slide-num {
  font-size: 96px;
  font-weight: 800;
  color: rgba(255,255,255,.15);
  user-select: none;
}
/* Badge overlay at bottom of slide */
.slide-badge {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  padding: 6px 12px;
  background: linear-gradient(to top, rgba(0,0,0,.65) 0%, transparent 100%);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
}
.slide-dur { margin-left:auto; font-size:12px; opacity:.85; }

/* Page title below slide */
.page-title-text {
  font-size: 18px;
  font-weight: 700;
  color: #1a1a2e;
  line-height: 1.4;
}

/* Talking points */
.points-section { display:flex; flex-direction:column; gap:8px; }
.points-label   { font-size:13px; font-weight:600; color:#606266; margin-bottom:4px; }
.talking-points {
  margin: 0;
  padding-left: 22px;
  font-size: 14px;
  color: #303133;
  line-height: 2;
}
.talking-points li.emphasis {
  font-weight: 700;
  color: #c05800;
}
.star { color:#e6700a; margin-right:4px; font-size:12px; }
.empty-point { list-style:none; color:#c0c4cc; padding-left:0; }

/* Transition hint */
.transition-hint {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 12px;
  color: #909399;
  background: #f5f7fa;
  border-radius: 6px;
  padding: 8px 10px;
  line-height: 1.6;
}

/* ── Right: practice column ── */
.practice-col {
  display: flex;
  flex-direction: column;
  gap: 14px;
  /* Stick to top when scrolling */
  position: sticky;
  top: 16px;
}

/* Shared panel */
.panel {
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  padding: 16px;
  background: #fff;
}
.panel-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 14px;
}
.demo-audio { width:100%; height:36px; }
.script-text { font-size:13px; line-height:1.8; color:#606266; white-space:pre-wrap; margin:0; }

/* Recording */
.record-body {
  text-align: center;
  padding: 20px 8px;
  border: 2px dashed #dcdfe6;
  border-radius: 10px;
}
.timer {
  font-size:28px; font-weight:700; color:#f56c6c;
  display:flex; align-items:center; justify-content:center;
  gap:8px; margin-bottom:16px;
}
.pulse { animation:pulse 1s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.2} }
.record-buttons { margin-bottom:12px; }
.hint { font-size:13px; color:#909399; margin-bottom:8px; text-align:left; }
.transcript-input { text-align:left; }

/* Score card */
.score-card {
  background:#f5f7fa; border-radius:12px; padding:16px;
  display:flex; flex-wrap:wrap; gap:16px; align-items:flex-start;
}
.score-total { display:flex; flex-direction:column; align-items:center; gap:6px; min-width:100px; }
.score-label { font-size:12px; color:#606266; }
.score-dims  { flex:1; min-width:180px; display:flex; flex-direction:column; gap:8px; }
.dim-item    { display:flex; align-items:center; gap:8px; }
.dim-name    { width:80px; font-size:12px; color:#606266; flex-shrink:0; }
.feedback-list { min-width:160px; }
.feedback-title { font-weight:600; margin-bottom:6px; font-size:13px; }
.feedback-list ul { margin:0; padding-left:16px; font-size:13px; color:#606266; line-height:1.8; }
.history-strip { width:100%; display:flex; align-items:center; gap:4px; font-size:12px; color:#909399; }
.history-label { margin-right:4px; }

/* History table */
.history-section { margin-top:4px; }
.section-title { font-weight:600; margin-bottom:10px; font-size:14px; }

.fade-enter-active,.fade-leave-active { transition:opacity .4s ease; }
.fade-enter-from,.fade-leave-to       { opacity:0; }
</style>
