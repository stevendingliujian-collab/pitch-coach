<template>
  <div class="pm-wrapper">
    <!-- Header -->
    <div class="pm-header">
      <div class="pm-header-left">
        <button class="back-btn" @click="$router.back()">← 返回</button>
        <div>
          <h1 class="pm-title">AI 复盘助手</h1>
          <p class="pm-subtitle">上传述标会议录音，AI 自动分析评委问题、回答质量和改进建议</p>
        </div>
      </div>
    </div>

    <div class="pm-content">
      <!-- Left: Upload + History List -->
      <div class="pm-sidebar">
        <!-- Upload card -->
        <div class="upload-card">
          <div class="upload-icon">🎙️</div>
          <p class="upload-label">上传述标会议录音</p>
          <p class="upload-hint">支持 MP3 / WAV / M4A，建议不超过 200MB</p>

          <div v-if="!selectedFile" class="upload-drop"
               @dragover.prevent @drop.prevent="onDrop"
               @click="fileInput?.click()">
            <span class="upload-drop-icon">📁</span>
            <span>点击选择文件或拖拽至此</span>
            <input ref="fileInput" type="file" accept=".mp3,.wav,.m4a,audio/*"
                   style="display:none" @change="onFileChange" />
          </div>

          <div v-else class="file-selected">
            <span class="file-name">📎 {{ selectedFile.name }}</span>
            <span class="file-size">{{ formatFileSize(selectedFile.size) }}</span>
            <button class="btn-remove" @click="selectedFile = null">✕</button>
          </div>

          <div v-if="uploadError" class="upload-error">{{ uploadError }}</div>

          <div class="task-select-row">
            <label>述标项目</label>
            <select v-model="selectedTaskId" class="task-select">
              <option :value="null" disabled>请选择项目</option>
              <option v-for="t in tasks" :key="t.id" :value="t.id">{{ t.name }}</option>
            </select>
          </div>

          <button class="btn-upload" :disabled="!selectedFile || !selectedTaskId || uploading"
                  @click="uploadRecording">
            <span v-if="uploading" class="spinner">⏳</span>
            {{ uploading ? '上传并分析中…' : '开始 AI 复盘分析' }}
          </button>
        </div>

        <!-- History list -->
        <div class="history-section">
          <h3 class="history-title">复盘历史</h3>
          <div v-if="loadingHistory" class="history-loading">加载中…</div>
          <div v-else-if="reports.length === 0" class="history-empty">
            暂无复盘记录，上传录音开始分析
          </div>
          <div v-else class="history-list">
            <div v-for="r in reports" :key="r.id"
                 class="history-item"
                 :class="{ active: selectedReport?.id === r.id, [r.status]: true }"
                 @click="selectReport(r.id)">
              <div class="history-item-top">
                <span class="status-dot" :class="r.status"></span>
                <span class="history-date">{{ formatDate(r.created_at) }}</span>
                <span v-if="r.overall_score !== null" class="history-score">{{ r.overall_score }}分</span>
              </div>
              <div class="history-item-bottom">
                <span class="history-meta">
                  {{ r.question_count ?? '—' }} 个问题
                  <template v-if="r.prediction_hit_rate !== null">
                    · 命中率 {{ Math.round(r.prediction_hit_rate * 100) }}%
                  </template>
                </span>
                <span v-if="r.status === 'processing'" class="processing-badge">分析中…</span>
                <span v-if="r.status === 'failed'" class="failed-badge">失败</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right: Report detail -->
      <div class="pm-main">
        <!-- Empty state -->
        <div v-if="!selectedReport && !loadingReport" class="empty-state">
          <div class="empty-icon">📊</div>
          <h2>选择或上传复盘报告</h2>
          <p>AI 将自动分析评委问题、识别回答质量、预测命中率，并草拟答疑跟进函</p>
          <div class="feature-list">
            <div class="feature-item">🎯 <span>评委问题提取与分类（技术/商务/用户/合规）</span></div>
            <div class="feature-item">📈 <span>排练预测命中率对比</span></div>
            <div class="feature-item">💬 <span>回答质量评估与改进建议</span></div>
            <div class="feature-item">✉️ <span>答疑跟进函一键草拟</span></div>
            <div class="feature-item">⚡ <span>关键时刻复盘（精彩/高压/转折）</span></div>
          </div>
        </div>

        <!-- Loading report -->
        <div v-else-if="loadingReport" class="report-loading">
          <div class="spinner-large">⏳</div>
          <p>加载复盘报告…</p>
        </div>

        <!-- Processing state -->
        <div v-else-if="selectedReport?.status === 'processing' || selectedReport?.status === 'pending'"
             class="processing-state">
          <div class="processing-icon">🔄</div>
          <h2>AI 正在分析中</h2>
          <p>通常需要 2-5 分钟，请稍候…</p>
          <div class="progress-steps">
            <div class="step done">✅ 上传完成</div>
            <div class="step active">⏳ AI 转录 + 说话人分离</div>
            <div class="step">⬜ 评委问题提取</div>
            <div class="step">⬜ 回答质量评估</div>
            <div class="step">⬜ 综合洞察生成</div>
          </div>
          <button class="btn-refresh" @click="refreshReport">🔄 刷新状态</button>
        </div>

        <!-- Failed state -->
        <div v-else-if="selectedReport?.status === 'failed'" class="failed-state">
          <div class="failed-icon">❌</div>
          <h2>分析失败</h2>
          <p class="error-msg">{{ selectedReport.error_msg || '未知错误，请重试' }}</p>
          <button class="btn-retry" @click="retryReport">重新分析</button>
        </div>

        <!-- Completed report -->
        <div v-else-if="selectedReport?.status === 'completed'" class="report-content">
          <!-- Overview bar -->
          <div class="report-overview">
            <div class="overview-score">
              <span class="score-num" :class="gradeClass(selectedReport.overall_score)">
                {{ selectedReport.overall_score ?? '—' }}
              </span>
              <span class="score-label">综合评分</span>
              <span class="grade-badge" :class="gradeClass(selectedReport.overall_score)">
                {{ selectedReport.grade || '' }}
              </span>
            </div>
            <div class="overview-stats">
              <div class="stat">
                <span class="stat-num">{{ selectedReport.question_count ?? 0 }}</span>
                <span class="stat-label">评委问题</span>
              </div>
              <div class="stat">
                <span class="stat-num">{{ selectedReport.evaluator_count ?? 1 }}</span>
                <span class="stat-label">评委人数</span>
              </div>
              <div class="stat">
                <span class="stat-num">{{ talkRatioStr }}</span>
                <span class="stat-label">我方发言占比</span>
              </div>
              <div class="stat" :class="hitRateClass">
                <span class="stat-num">{{ hitRateStr }}</span>
                <span class="stat-label">预测命中率</span>
              </div>
            </div>
          </div>

          <!-- Tabs -->
          <div class="report-tabs">
            <button v-for="tab in reportTabs" :key="tab.key"
                    class="report-tab"
                    :class="{ active: activeTab === tab.key }"
                    @click="activeTab = tab.key">
              {{ tab.label }}
            </button>
          </div>

          <!-- Tab: 洞察 -->
          <div v-if="activeTab === 'insights'" class="tab-panel">
            <div v-if="selectedReport.insights" class="insights-grid">
              <div class="insight-card strengths">
                <h4>✅ 优势亮点</h4>
                <ul>
                  <li v-for="(s, i) in selectedReport.insights.strengths" :key="i">{{ s }}</li>
                </ul>
              </div>
              <div class="insight-card weaknesses">
                <h4>⚠️ 不足之处</h4>
                <ul>
                  <li v-for="(w, i) in selectedReport.insights.weaknesses" :key="i">{{ w }}</li>
                </ul>
              </div>
              <div class="insight-card risks">
                <h4>🚨 风险项</h4>
                <ul>
                  <li v-for="(r, i) in selectedReport.insights.top_risks" :key="i">{{ r }}</li>
                </ul>
              </div>
              <div class="insight-card focus">
                <h4>🎯 下次排练重点</h4>
                <ul>
                  <li v-for="(f, i) in selectedReport.insights.next_rehearsal_focus" :key="i">{{ f }}</li>
                </ul>
              </div>
            </div>

            <!-- Action items -->
            <div v-if="selectedReport.insights?.action_items?.length" class="action-items">
              <h4>📋 行动清单</h4>
              <div v-for="(a, i) in selectedReport.insights.action_items" :key="i"
                   class="action-item" :class="a.priority">
                <span class="priority-badge">{{ a.priority === 'high' ? '🔴 紧急' : '🟡 重要' }}</span>
                <span class="action-text">{{ a.action }}</span>
                <span v-if="a.deadline" class="action-deadline">{{ a.deadline }}</span>
              </div>
            </div>
          </div>

          <!-- Tab: 评委问题 -->
          <div v-if="activeTab === 'questions'" class="tab-panel">
            <!-- Category pills -->
            <div class="category-pills">
              <button v-for="(count, cat) in selectedReport.question_categories" :key="cat"
                      class="cat-pill"
                      :class="{ active: filterCategory === cat }"
                      @click="filterCategory = filterCategory === cat ? null : cat">
                {{ categoryName(cat) }} ({{ count }})
              </button>
            </div>

            <div class="questions-list">
              <div v-for="q in filteredQuestions" :key="q.id" class="question-card"
                   :class="{ risky: q.is_risky }">
                <div class="question-header">
                  <span class="q-category">{{ q.category_name }}</span>
                  <span class="q-type">{{ q.question_type }}</span>
                  <span v-if="q.is_risky" class="risky-badge">⚠️ 高风险</span>
                  <div class="q-quality">
                    <span v-for="n in 5" :key="n"
                          class="quality-dot" :class="{ filled: n <= q.answer_quality }"></span>
                    <span class="quality-label">{{ qualityLabel(q.answer_quality) }}</span>
                  </div>
                </div>
                <p class="question-text">❓ {{ q.question }}</p>
                <p v-if="q.answer_text" class="answer-text">💬 {{ q.answer_text }}</p>
                <p v-if="q.notes" class="q-notes">📝 {{ q.notes }}</p>

                <!-- Matching assessment -->
                <div v-if="getAssessment(q.id)" class="assessment-block">
                  <p class="assessment-feedback">{{ getAssessment(q.id)!.feedback }}</p>
                  <p class="assessment-suggestion">💡 {{ getAssessment(q.id)!.suggestion }}</p>
                  <ul v-if="getAssessment(q.id)!.ideal_answer_outline" class="ideal-outline">
                    <li>理想回答要点：{{ getAssessment(q.id)!.ideal_answer_outline }}</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          <!-- Tab: 关键时刻 -->
          <div v-if="activeTab === 'moments'" class="tab-panel">
            <div v-if="!selectedReport.key_moments?.length" class="empty-tab">
              未识别到关键时刻
            </div>
            <div v-else class="moments-timeline">
              <div v-for="(m, i) in selectedReport.key_moments" :key="i"
                   class="moment-item" :class="m.type">
                <div class="moment-icon">{{ momentIcon(m.type) }}</div>
                <div class="moment-body">
                  <div class="moment-header">
                    <span class="moment-type">{{ momentLabel(m.type) }}</span>
                    <span class="moment-speaker">{{ m.speaker }}</span>
                    <div class="moment-importance">
                      <span v-for="n in 5" :key="n" class="imp-dot"
                            :class="{ filled: n <= m.importance }"></span>
                    </div>
                  </div>
                  <p class="moment-text">"{{ m.text }}"</p>
                  <p class="moment-analysis">{{ m.analysis }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Tab: 答疑函 -->
          <div v-if="activeTab === 'followup'" class="tab-panel">
            <div class="followup-toolbar">
              <h3>📧 答疑跟进函草稿</h3>
              <button class="btn-copy" @click="copyFollowup">📋 复制全文</button>
            </div>
            <div v-if="selectedReport.followup_draft" class="followup-content">
              <pre class="followup-text">{{ selectedReport.followup_draft }}</pre>
            </div>
            <div v-else class="empty-tab">暂无答疑函草稿</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { postMortemApi, type PostMortemSummary, type PostMortemReport, type EvaluatorQuestion, type AnswerAssessment } from '@/api/postMortem'
import { api } from '@/api/index'

// ── State ──────────────────────────────────────────────────────────────────
const route = useRoute()
const tasks = ref<Array<{ id: number; name: string }>>([])
const selectedTaskId = ref<number | null>(
  route.query.taskId ? Number(route.query.taskId) : null
)
const reports = ref<PostMortemSummary[]>([])
const selectedReport = ref<PostMortemReport | null>(null)
const loadingHistory = ref(false)
const loadingReport = ref(false)
const uploading = ref(false)
const selectedFile = ref<File | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const uploadError = ref('')
const activeTab = ref<'insights' | 'questions' | 'moments' | 'followup'>('insights')
const filterCategory = ref<string | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

const reportTabs = [
  { key: 'insights', label: '📊 洞察总结' },
  { key: 'questions', label: '❓ 评委问题' },
  { key: 'moments', label: '⚡ 关键时刻' },
  { key: 'followup', label: '✉️ 答疑函' },
] as const

// ── Computed ───────────────────────────────────────────────────────────────
const talkRatioStr = computed(() => {
  const r = selectedReport.value?.our_talk_ratio
  return r != null ? `${Math.round(r * 100)}%` : '—'
})

const hitRateStr = computed(() => {
  const r = selectedReport.value?.prediction_hit_rate
  return r != null ? `${Math.round(r * 100)}%` : '—'
})

const hitRateClass = computed(() => {
  const r = selectedReport.value?.prediction_hit_rate
  if (r == null) return ''
  if (r >= 0.7) return 'stat-good'
  if (r >= 0.4) return 'stat-medium'
  return 'stat-bad'
})

const filteredQuestions = computed((): EvaluatorQuestion[] => {
  const qs = selectedReport.value?.evaluator_questions ?? []
  if (!filterCategory.value) return qs
  return qs.filter((q) => q.category === filterCategory.value)
})

// ── Lifecycle ──────────────────────────────────────────────────────────────
onMounted(async () => {
  await loadTasks()
  if (selectedTaskId.value) await loadHistory(selectedTaskId.value)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

// ── Methods ────────────────────────────────────────────────────────────────
async function loadTasks() {
  try {
    const res = await api.get<Array<{ id: number; name: string }>>('/pitch-tasks')
    tasks.value = res.data
  } catch {
    tasks.value = []
  }
}

async function loadHistory(taskId: number) {
  loadingHistory.value = true
  try {
    const res = await postMortemApi.list(taskId)
    reports.value = res.data
    // Auto-select first completed
    const first = res.data.find((r) => r.status === 'completed') ?? res.data[0]
    if (first) await selectReport(first.id)
  } finally {
    loadingHistory.value = false
  }
}

async function selectReport(id: number) {
  loadingReport.value = true
  try {
    const res = await postMortemApi.get(id)
    selectedReport.value = res.data
    activeTab.value = 'insights'
    filterCategory.value = null
    // Poll if still processing
    if (res.data.status === 'processing' || res.data.status === 'pending') {
      startPolling(id)
    }
  } finally {
    loadingReport.value = false
  }
}

function startPolling(id: number) {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    try {
      const res = await postMortemApi.get(id)
      selectedReport.value = res.data
      // Update summary in list
      const idx = reports.value.findIndex((r) => r.id === id)
      if (idx >= 0) {
        reports.value[idx] = {
          ...reports.value[idx],
          status: res.data.status,
          question_count: res.data.question_count,
          prediction_hit_rate: res.data.prediction_hit_rate,
          overall_score: res.data.overall_score,
          grade: res.data.grade,
        }
      }
      if (res.data.status === 'completed' || res.data.status === 'failed') {
        if (pollTimer) clearInterval(pollTimer)
      }
    } catch {
      // ignore
    }
  }, 5000)
}

async function refreshReport() {
  if (!selectedReport.value) return
  await selectReport(selectedReport.value.id)
}

async function retryReport() {
  if (!selectedReport.value) return
  try {
    await postMortemApi.retry(selectedReport.value.id)
    selectedReport.value.status = 'pending'
    startPolling(selectedReport.value.id)
  } catch (e: any) {
    alert('重试失败：' + (e.response?.data?.detail || e.message))
  }
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) selectedFile.value = input.files[0]
}

function onDrop(e: DragEvent) {
  const file = e.dataTransfer?.files?.[0]
  if (file) selectedFile.value = file
}

async function uploadRecording() {
  if (!selectedFile.value || !selectedTaskId.value) return
  uploading.value = true
  uploadError.value = ''
  try {
    const res = await postMortemApi.create(selectedTaskId.value, selectedFile.value)
    selectedFile.value = null
    // Refresh history and select new report
    await loadHistory(selectedTaskId.value)
    await selectReport(res.data.id)
  } catch (e: any) {
    uploadError.value = e.response?.data?.detail || '上传失败，请重试'
  } finally {
    uploading.value = false
  }
}

function getAssessment(questionId: number): AnswerAssessment | undefined {
  return selectedReport.value?.answer_assessments?.find((a) => a.question_id === questionId)
}

function copyFollowup() {
  const text = selectedReport.value?.followup_draft || ''
  navigator.clipboard.writeText(text).then(() => alert('已复制到剪贴板'))
}

// ── Formatters ────────────────────────────────────────────────────────────
function formatDate(iso: string) {
  return new Date(iso).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function formatFileSize(bytes: number) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function gradeClass(score: number | null) {
  if (score == null) return ''
  if (score >= 85) return 'grade-excellent'
  if (score >= 70) return 'grade-good'
  if (score >= 55) return 'grade-fair'
  return 'grade-poor'
}

function qualityLabel(q: number) {
  return ['', '很差', '较差', '一般', '良好', '优秀'][q] ?? ''
}

function momentIcon(type: string) {
  return { highlight: '✨', pressure: '🔥', turning_point: '🔀', missed: '💭' }[type] ?? '📍'
}

function momentLabel(type: string) {
  return { highlight: '精彩回答', pressure: '高压时刻', turning_point: '关键转折', missed: '错失机会' }[type] ?? type
}

function categoryName(cat: string) {
  return { tech: '技术类', business: '商务类', user: '用户/运维', compliance: '合规类', other: '其他' }[cat] ?? cat
}
</script>

<style scoped>
.pm-wrapper { display: flex; flex-direction: column; height: 100vh; background: #F5F5F7; }

.pm-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 24px; background: #fff; border-bottom: 1px solid #e5e7eb;
}
.pm-header-left { display: flex; align-items: center; gap: 16px; }
.back-btn {
  padding: 6px 12px; border: 1px solid #e5e7eb; border-radius: 6px;
  background: #fff; cursor: pointer; font-size: 13px; color: #6b7280;
}
.back-btn:hover { background: #f9fafb; }
.pm-title { font-size: 20px; font-weight: 700; color: #111827; margin: 0; }
.pm-subtitle { font-size: 13px; color: #6b7280; margin: 2px 0 0; }

.pm-content { display: flex; flex: 1; overflow: hidden; }

/* ── Sidebar ── */
.pm-sidebar {
  width: 300px; background: #fff; border-right: 1px solid #e5e7eb;
  overflow-y: auto; display: flex; flex-direction: column; gap: 0;
}

.upload-card { padding: 20px; border-bottom: 1px solid #e5e7eb; }
.upload-icon { font-size: 28px; margin-bottom: 6px; }
.upload-label { font-weight: 600; font-size: 14px; color: #111827; margin: 0 0 2px; }
.upload-hint { font-size: 12px; color: #9ca3af; margin: 0 0 12px; }

.upload-drop {
  border: 2px dashed #d1d5db; border-radius: 8px; padding: 16px;
  text-align: center; cursor: pointer; font-size: 13px; color: #6b7280;
  transition: border-color .15s;
}
.upload-drop:hover { border-color: #6366F1; color: #6366F1; }
.upload-drop-icon { display: block; font-size: 20px; margin-bottom: 4px; }

.file-selected {
  display: flex; align-items: center; gap: 8px; padding: 8px 10px;
  background: #f0f0ff; border-radius: 6px; font-size: 13px;
}
.file-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #4b5563; }
.file-size { color: #9ca3af; font-size: 11px; }
.btn-remove { background: none; border: none; cursor: pointer; color: #ef4444; font-size: 14px; }

.upload-error { font-size: 12px; color: #ef4444; margin-top: 6px; }

.task-select-row { display: flex; flex-direction: column; gap: 4px; margin: 12px 0 10px; }
.task-select-row label { font-size: 12px; color: #6b7280; }
.task-select {
  width: 100%; padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px;
  font-size: 13px; background: #fff;
}

.btn-upload {
  width: 100%; padding: 9px; background: #6366F1; color: #fff;
  border: none; border-radius: 8px; font-size: 14px; font-weight: 600;
  cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px;
  transition: background .15s;
}
.btn-upload:hover:not(:disabled) { background: #4f46e5; }
.btn-upload:disabled { background: #c7d2fe; cursor: not-allowed; }

.history-section { padding: 16px; flex: 1; }
.history-title { font-size: 13px; font-weight: 600; color: #374151; margin: 0 0 10px; }
.history-loading, .history-empty { font-size: 13px; color: #9ca3af; text-align: center; padding: 20px 0; }

.history-item {
  padding: 10px; border-radius: 8px; cursor: pointer; margin-bottom: 6px;
  border: 1px solid #e5e7eb; transition: all .15s;
}
.history-item:hover { border-color: #6366F1; background: #f5f5ff; }
.history-item.active { border-color: #6366F1; background: #eef2ff; }

.history-item-top { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
.status-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.status-dot.completed { background: #22c55e; }
.status-dot.processing, .status-dot.pending { background: #f59e0b; }
.status-dot.failed { background: #ef4444; }
.history-date { font-size: 12px; color: #6b7280; flex: 1; }
.history-score { font-size: 13px; font-weight: 700; color: #6366F1; }
.history-item-bottom { display: flex; align-items: center; gap: 8px; }
.history-meta { font-size: 12px; color: #9ca3af; flex: 1; }
.processing-badge { font-size: 11px; color: #f59e0b; }
.failed-badge { font-size: 11px; color: #ef4444; }

/* ── Main ── */
.pm-main { flex: 1; overflow-y: auto; padding: 24px; }

.empty-state {
  display: flex; flex-direction: column; align-items: center; text-align: center;
  padding: 60px 40px; color: #6b7280;
}
.empty-icon { font-size: 48px; margin-bottom: 16px; }
.empty-state h2 { font-size: 20px; color: #111827; margin: 0 0 8px; }
.empty-state p { font-size: 14px; max-width: 400px; line-height: 1.6; }
.feature-list { margin-top: 24px; text-align: left; display: flex; flex-direction: column; gap: 10px; }
.feature-item { display: flex; gap: 10px; font-size: 14px; color: #374151; }

.report-loading { text-align: center; padding: 80px; color: #6b7280; }
.spinner-large { font-size: 40px; display: block; margin-bottom: 12px; }

.processing-state, .failed-state {
  text-align: center; padding: 60px 40px; color: #6b7280;
}
.processing-icon, .failed-icon { font-size: 48px; margin-bottom: 16px; display: block; }
.processing-state h2, .failed-state h2 { font-size: 20px; color: #111827; margin: 0 0 8px; }
.progress-steps { display: flex; flex-direction: column; gap: 8px; margin: 24px 0; text-align: left; max-width: 300px; }
.step { font-size: 14px; color: #6b7280; padding: 6px 10px; border-radius: 6px; }
.step.done { color: #16a34a; background: #f0fdf4; }
.step.active { color: #d97706; background: #fffbeb; }
.btn-refresh, .btn-retry {
  margin-top: 16px; padding: 8px 20px; border-radius: 6px;
  border: 1px solid #6366F1; color: #6366F1; background: #fff;
  cursor: pointer; font-size: 14px;
}
.btn-retry { border-color: #ef4444; color: #ef4444; }
.error-msg { font-size: 13px; color: #ef4444; margin: 8px 0; }

/* ── Report content ── */
.report-overview {
  display: flex; align-items: center; gap: 32px; padding: 20px 24px;
  background: #fff; border-radius: 12px; margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,.06);
}
.overview-score { text-align: center; }
.score-num { font-size: 48px; font-weight: 800; display: block; line-height: 1; }
.score-label { font-size: 12px; color: #9ca3af; display: block; margin-top: 2px; }
.grade-badge {
  display: inline-block; padding: 2px 10px; border-radius: 20px;
  font-size: 12px; font-weight: 600; margin-top: 4px;
}
.grade-excellent { color: #16a34a; }
.grade-excellent.grade-badge { background: #dcfce7; }
.grade-good { color: #6366F1; }
.grade-good.grade-badge { background: #eef2ff; }
.grade-fair { color: #d97706; }
.grade-fair.grade-badge { background: #fffbeb; }
.grade-poor { color: #ef4444; }
.grade-poor.grade-badge { background: #fef2f2; }

.overview-stats { display: flex; gap: 24px; }
.stat { text-align: center; }
.stat-num { font-size: 24px; font-weight: 700; color: #111827; display: block; }
.stat-label { font-size: 12px; color: #9ca3af; display: block; margin-top: 2px; }
.stat-good .stat-num { color: #16a34a; }
.stat-medium .stat-num { color: #d97706; }
.stat-bad .stat-num { color: #ef4444; }

.report-tabs { display: flex; gap: 8px; margin-bottom: 16px; }
.report-tab {
  padding: 7px 16px; border-radius: 8px; border: 1px solid #e5e7eb;
  background: #fff; cursor: pointer; font-size: 13px; color: #6b7280;
  transition: all .15s;
}
.report-tab.active { background: #6366F1; color: #fff; border-color: #6366F1; }
.report-tab:hover:not(.active) { border-color: #6366F1; color: #6366F1; }

.tab-panel { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,.06); }

.insights-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }
.insight-card {
  border-radius: 10px; padding: 16px;
}
.insight-card h4 { font-size: 14px; font-weight: 600; margin: 0 0 10px; }
.insight-card ul { margin: 0; padding: 0 0 0 16px; }
.insight-card li { font-size: 13px; color: #374151; line-height: 1.6; }
.strengths { background: #f0fdf4; }
.strengths h4 { color: #16a34a; }
.weaknesses { background: #fef2f2; }
.weaknesses h4 { color: #ef4444; }
.risks { background: #fff7ed; }
.risks h4 { color: #d97706; }
.focus { background: #eef2ff; }
.focus h4 { color: #6366F1; }

.action-items { margin-top: 4px; }
.action-items h4 { font-size: 14px; font-weight: 600; color: #111827; margin: 0 0 10px; }
.action-item {
  display: flex; align-items: center; gap: 10px; padding: 8px 12px;
  border-radius: 8px; margin-bottom: 6px; font-size: 13px;
}
.action-item.high { background: #fef2f2; }
.action-item.medium { background: #fffbeb; }
.priority-badge { font-size: 12px; font-weight: 600; flex-shrink: 0; }
.action-text { flex: 1; color: #374151; }
.action-deadline { font-size: 11px; color: #9ca3af; }

.category-pills { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.cat-pill {
  padding: 4px 12px; border-radius: 20px; border: 1px solid #e5e7eb;
  background: #fff; cursor: pointer; font-size: 12px; color: #6b7280;
  transition: all .15s;
}
.cat-pill.active { background: #6366F1; color: #fff; border-color: #6366F1; }

.questions-list { display: flex; flex-direction: column; gap: 12px; }
.question-card {
  border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px;
  transition: border-color .15s;
}
.question-card.risky { border-color: #fca5a5; background: #fff8f8; }
.question-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
.q-category {
  font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px;
  background: #eef2ff; color: #6366F1;
}
.q-type { font-size: 11px; color: #9ca3af; }
.risky-badge { font-size: 11px; color: #ef4444; }
.q-quality { display: flex; align-items: center; gap: 3px; margin-left: auto; }
.quality-dot { width: 8px; height: 8px; border-radius: 2px; background: #e5e7eb; }
.quality-dot.filled { background: #6366F1; }
.quality-label { font-size: 11px; color: #9ca3af; margin-left: 4px; }
.question-text { font-size: 14px; color: #111827; margin: 0 0 6px; font-weight: 500; }
.answer-text { font-size: 13px; color: #374151; margin: 0 0 6px; }
.q-notes { font-size: 12px; color: #9ca3af; margin: 0 0 8px; }
.assessment-block {
  border-top: 1px solid #e5e7eb; margin-top: 8px; padding-top: 8px;
}
.assessment-feedback { font-size: 13px; color: #374151; margin: 0 0 4px; }
.assessment-suggestion { font-size: 13px; color: #6366F1; margin: 0 0 4px; }
.ideal-outline { font-size: 12px; color: #6b7280; margin: 4px 0 0; padding-left: 16px; }

.moments-timeline { display: flex; flex-direction: column; gap: 14px; }
.moment-item { display: flex; gap: 12px; }
.moment-icon { font-size: 22px; flex-shrink: 0; margin-top: 2px; }
.moment-body { flex: 1; border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px; }
.moment-item.highlight .moment-body { border-color: #bbf7d0; background: #f0fdf4; }
.moment-item.pressure .moment-body { border-color: #fca5a5; background: #fff8f8; }
.moment-item.turning_point .moment-body { border-color: #c4b5fd; background: #f5f3ff; }
.moment-item.missed .moment-body { border-color: #fde68a; background: #fffbeb; }
.moment-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.moment-type { font-size: 12px; font-weight: 600; color: #374151; }
.moment-speaker { font-size: 12px; color: #9ca3af; }
.moment-importance { display: flex; gap: 2px; margin-left: auto; }
.imp-dot { width: 6px; height: 6px; border-radius: 50%; background: #e5e7eb; }
.imp-dot.filled { background: #6366F1; }
.moment-text { font-size: 14px; color: #111827; margin: 0 0 4px; font-style: italic; }
.moment-analysis { font-size: 12px; color: #6b7280; margin: 0; }

.followup-toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.followup-toolbar h3 { font-size: 15px; font-weight: 600; margin: 0; }
.btn-copy {
  padding: 6px 14px; border: 1px solid #e5e7eb; border-radius: 6px;
  background: #fff; cursor: pointer; font-size: 13px; color: #374151;
  transition: all .15s;
}
.btn-copy:hover { border-color: #6366F1; color: #6366F1; }
.followup-content {
  background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px;
  max-height: 60vh; overflow-y: auto;
}
.followup-text { font-size: 14px; color: #374151; line-height: 1.8; white-space: pre-wrap; margin: 0; font-family: inherit; }
.empty-tab { text-align: center; padding: 40px; color: #9ca3af; font-size: 14px; }

.spinner { font-size: 16px; }
</style>
