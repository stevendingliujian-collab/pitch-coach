<template>
  <div class="evaluator-page v2-page">
    <!-- Top bar -->
    <div class="v2-topbar ev-topbar">
      <button class="ev-back-btn" @click="router.push('/projects')">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="9 2 4 7 9 12"/>
        </svg>
        返回项目
      </button>
      <span class="v2-topbar-flex" />
      <div v-if="currentSession" class="session-status-badge" :class="sessionStatusClass">
        {{ sessionStatusLabel }}
      </div>
    </div>

    <!-- Phase: select persona -->
    <div v-if="phase === 'select'" class="ev-select-phase">
      <div class="ev-hero">
        <div class="ev-hero-icon">🎭</div>
        <h2 class="ev-hero-title">模拟评委问答</h2>
        <p class="ev-hero-desc">选择一位评委，练习如何应对评标现场的刁钻问题</p>
      </div>

      <!-- Task picker -->
      <div class="task-picker-wrap">
        <label class="picker-label">选择述标项目</label>
        <select class="picker-select" v-model="selectedTaskId">
          <option :value="null" disabled>请选择项目…</option>
          <option v-for="task in tasks" :key="task.id" :value="task.id">
            {{ task.name }}
          </option>
        </select>
      </div>

      <!-- Persona cards -->
      <div class="persona-grid">
        <div
          v-for="persona in personas"
          :key="persona.id"
          class="persona-card"
          :class="{ selected: selectedPersonaId === persona.id }"
          @click="selectedPersonaId = persona.id"
        >
          <div class="persona-avatar">{{ persona.avatar_emoji }}</div>
          <div class="persona-name">{{ persona.name }}</div>
          <div class="persona-role">{{ persona.role }}</div>
          <div class="persona-desc">{{ persona.description }}</div>
          <div class="persona-meta">
            <div class="difficulty-bar">
              <div
                v-for="n in 5"
                :key="n"
                class="difficulty-dot"
                :class="{ active: n <= persona.difficulty }"
              />
            </div>
            <span class="difficulty-label">难度 {{ persona.difficulty }}/5</span>
          </div>
          <div class="focus-tags">
            <span v-for="tag in (persona.focus_areas || []).slice(0, 3)" :key="tag" class="focus-tag">
              {{ tag }}
            </span>
          </div>
        </div>
      </div>

      <div class="ev-start-bar">
        <button
          class="btn-start"
          :disabled="!selectedPersonaId || !selectedTaskId || starting"
          @click="startSession"
        >
          <svg v-if="starting" class="spin" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M8 2a6 6 0 110 12A6 6 0 018 2" stroke-dasharray="28" stroke-dashoffset="14"/>
          </svg>
          {{ starting ? '评委正在准备问题…' : '开始模拟问答' }}
        </button>
        <span class="start-hint">AI 将根据你的述标内容生成针对性问题</span>
      </div>

      <!-- Past sessions -->
      <div v-if="pastSessions.length" class="past-sessions">
        <h3 class="ps-title">历史问答记录</h3>
        <div class="ps-list">
          <div
            v-for="s in pastSessions"
            :key="s.id"
            class="ps-item"
            @click="viewSession(s)"
          >
            <div class="ps-meta">
              <span class="ps-date">{{ formatDate(s.created_at) }}</span>
              <span class="ps-status" :class="s.status === 2 ? 'completed' : 'in-progress'">
                {{ s.status === 2 ? '已完成' : '进行中' }}
              </span>
            </div>
            <div class="ps-score" v-if="s.total_score !== null">
              <span class="ps-score-num" :class="scoreClass(s.total_score)">{{ Math.round(s.total_score) }}</span>
              <span class="ps-score-label">分</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Phase: chat -->
    <div v-else-if="phase === 'chat'" class="ev-chat-phase">
      <div class="ev-chat-layout">
        <!-- Persona panel -->
        <div class="ev-persona-panel">
          <div class="ep-avatar">{{ currentPersona?.avatar_emoji }}</div>
          <div class="ep-name">{{ currentPersona?.name }}</div>
          <div class="ep-role">{{ currentPersona?.role }}</div>
          <div class="ep-desc">{{ currentPersona?.description }}</div>
          <div class="ep-focus-areas">
            <div class="ep-fa-label">关注点</div>
            <span v-for="area in (currentPersona?.focus_areas || [])" :key="area" class="ep-fa-tag">
              {{ area }}
            </span>
          </div>
          <button class="btn-end-session" @click="endSession">
            结束问答
          </button>
        </div>

        <!-- Chat area -->
        <div class="ev-chat-area">
          <!-- Messages -->
          <div class="ev-messages" ref="messagesEl">
            <div
              v-for="(msg, i) in currentSession!.messages"
              :key="i"
              class="ev-message"
              :class="msg.role"
            >
              <div v-if="msg.role === 'evaluator'" class="msg-avatar evaluator">
                {{ currentPersona?.avatar_emoji }}
              </div>
              <div class="msg-bubble" :class="msg.role">
                <div class="msg-content">{{ msg.content }}</div>
              </div>
              <div v-if="msg.role === 'user'" class="msg-avatar user">我</div>
            </div>

            <!-- Typing indicator -->
            <div v-if="thinking" class="ev-message evaluator">
              <div class="msg-avatar evaluator">{{ currentPersona?.avatar_emoji }}</div>
              <div class="msg-bubble evaluator typing">
                <span class="dot" />
                <span class="dot" />
                <span class="dot" />
              </div>
            </div>
          </div>

          <!-- Input area -->
          <div class="ev-input-area" v-if="currentSession?.status !== 2">
            <div class="ev-input-row">
              <textarea
                class="ev-textarea"
                v-model="userInput"
                placeholder="输入你的回答…（支持粘贴，Ctrl+Enter 发送）"
                @keydown.ctrl.enter="submitAnswer"
                rows="3"
                :disabled="submitting"
              />
              <button
                class="btn-send"
                :disabled="!userInput.trim() || submitting"
                @click="submitAnswer"
              >
                <svg v-if="submitting" class="spin" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M8 2a6 6 0 110 12A6 6 0 018 2" stroke-dasharray="28" stroke-dashoffset="14"/>
                </svg>
                <svg v-else width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="2" y1="8" x2="14" y2="8"/><polyline points="9 3 14 8 9 13"/>
                </svg>
              </button>
            </div>
            <div class="ev-input-hint">Ctrl+Enter 发送 · 回答完所有问题后自动评分</div>
          </div>

          <!-- Score summary -->
          <div v-if="currentSession?.status === 2" class="ev-score-summary">
            <div class="ess-title">🎉 问答结束！</div>
            <div class="ess-score-row">
              <div class="ess-score" :class="scoreClass(currentSession.total_score || 0)">
                {{ Math.round(currentSession.total_score || 0) }}
              </div>
              <div class="ess-score-label">综合得分 / 100</div>
            </div>
            <div class="ess-feedback">{{ currentSession.feedback }}</div>
            <div class="ess-actions">
              <button class="btn-outline" @click="resetToSelect">再换一位评委</button>
              <button class="btn-primary" @click="router.push('/projects')">返回项目</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { evaluatorsApi, type EvaluatorPersona, type QASession } from '@/api/evaluators'
import { pitchTaskApi, type PitchTask } from '@/api/pitchTask'

const route = useRoute()
const router = useRouter()

const phase = ref<'select' | 'chat'>('select')
const personas = ref<EvaluatorPersona[]>([])
const tasks = ref<PitchTask[]>([])
const pastSessions = ref<QASession[]>([])
const selectedPersonaId = ref<string | number | null>(null)
const selectedTaskId = ref<number | null>(null)
const currentSession = ref<QASession | null>(null)
const starting = ref(false)
const submitting = ref(false)
const thinking = ref(false)
const userInput = ref('')
const messagesEl = ref<HTMLElement | null>(null)

const currentPersona = computed(() =>
  personas.value.find(p => String(p.id) === String(selectedPersonaId.value)) ?? null
)

const sessionStatusClass = computed(() => {
  if (!currentSession.value) return ''
  return currentSession.value.status === 2 ? 'completed' : 'in-progress'
})

const sessionStatusLabel = computed(() => {
  if (!currentSession.value) return ''
  return currentSession.value.status === 2 ? '已完成' : '问答进行中'
})

onMounted(async () => {
  // Load presets + tasks in parallel
  const [personasRes, tasksRes, sessionsRes] = await Promise.allSettled([
    evaluatorsApi.listPresets(),
    pitchTaskApi.list(),
    evaluatorsApi.listSessions(),
  ])
  if (personasRes.status === 'fulfilled') personas.value = personasRes.value.data
  if (tasksRes.status === 'fulfilled') tasks.value = tasksRes.value.data
  if (sessionsRes.status === 'fulfilled') pastSessions.value = sessionsRes.value.data

  // Pre-select task from route query
  const taskId = route.query.task_id
  if (taskId) selectedTaskId.value = Number(taskId)
})

watch(
  () => currentSession.value?.messages.length,
  async () => {
    await nextTick()
    if (messagesEl.value) {
      messagesEl.value.scrollTop = messagesEl.value.scrollHeight
    }
  }
)

async function startSession() {
  if (!selectedPersonaId.value || !selectedTaskId.value) return
  starting.value = true
  try {
    const res = await evaluatorsApi.startSession(selectedTaskId.value, {
      preset_persona_id: String(selectedPersonaId.value),
    })
    currentSession.value = res.data
    phase.value = 'chat'
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '启动失败，请稍后重试')
  } finally {
    starting.value = false
  }
}

async function submitAnswer() {
  if (!userInput.value.trim() || !currentSession.value) return
  const answer = userInput.value.trim()
  userInput.value = ''
  submitting.value = true
  thinking.value = true
  try {
    const res = await evaluatorsApi.submitAnswer(currentSession.value.id, answer)
    currentSession.value = res.data
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '提交失败')
    userInput.value = answer  // restore
  } finally {
    submitting.value = false
    thinking.value = false
  }
}

async function endSession() {
  if (!currentSession.value) return
  try {
    const res = await evaluatorsApi.completeSession(currentSession.value.id)
    currentSession.value = res.data
  } catch (e: any) {
    ElMessage.error('结束失败')
  }
}

function viewSession(s: QASession) {
  currentSession.value = s
  // Try to find persona from session
  phase.value = 'chat'
}

function resetToSelect() {
  phase.value = 'select'
  currentSession.value = null
  userInput.value = ''
}

function scoreClass(score: number) {
  if (score >= 80) return 'green'
  if (score >= 60) return 'orange'
  return 'red'
}

function formatDate(iso: string) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>

<style scoped>
.evaluator-page { background: var(--bg-content); min-height: 100vh; }

/* Top bar */
.ev-topbar { gap: 8px; }
.ev-back-btn {
  display: flex; align-items: center; gap: 5px;
  background: none; border: none; font-size: 13px; font-weight: 500;
  color: var(--t-muted); cursor: pointer; padding: 4px 8px; border-radius: 6px;
  transition: all 0.15s; font-family: inherit;
}
.ev-back-btn:hover { background: rgba(0,0,0,0.05); color: var(--t-primary); }
.session-status-badge {
  padding: 4px 12px; border-radius: 20px;
  font-size: 12px; font-weight: 700;
}
.session-status-badge.in-progress { background: rgba(249,115,22,0.1); color: #F97316; }
.session-status-badge.completed   { background: rgba(34,197,94,0.1);  color: #22C55E; }

/* ── Select phase ─────────────────────────────── */
.ev-select-phase {
  max-width: 960px; margin: 0 auto;
  padding: 32px 24px 80px;
}
.ev-hero { text-align: center; margin-bottom: 32px; }
.ev-hero-icon { font-size: 40px; margin-bottom: 12px; }
.ev-hero-title { font-size: 24px; font-weight: 800; color: var(--t-primary, #0F0F13); margin: 0 0 8px; }
.ev-hero-desc { font-size: 14px; color: var(--t-muted, #8B8D99); }

.task-picker-wrap { margin-bottom: 28px; }
.picker-label { font-size: 12.5px; font-weight: 700; color: var(--t-muted); display: block; margin-bottom: 6px; }
.picker-select {
  height: 38px; border-radius: 9px;
  border: 1.5px solid var(--border, rgba(0,0,0,0.12));
  background: #fff; font-size: 13.5px; padding: 0 12px;
  color: var(--t-primary, #0F0F13); min-width: 280px;
  cursor: pointer;
}

.persona-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
  margin-bottom: 28px;
}
.persona-card {
  background: #fff;
  border-radius: 14px;
  border: 1.5px solid var(--border, rgba(0,0,0,0.07));
  padding: 20px 16px;
  cursor: pointer; transition: all 0.15s;
  display: flex; flex-direction: column; gap: 6px;
}
.persona-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.08); transform: translateY(-1px); }
.persona-card.selected { border-color: #6366F1; box-shadow: 0 0 0 3px rgba(99,102,241,0.12); }
.persona-avatar { font-size: 32px; line-height: 1; }
.persona-name { font-size: 15px; font-weight: 800; color: var(--t-primary, #0F0F13); }
.persona-role { font-size: 11px; font-weight: 700; color: #6366F1; }
.persona-desc { font-size: 12px; color: var(--t-muted, #8B8D99); line-height: 1.5; }
.persona-meta { display: flex; align-items: center; gap: 8px; }
.difficulty-bar { display: flex; gap: 3px; }
.difficulty-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: rgba(0,0,0,0.08);
}
.difficulty-dot.active { background: #6366F1; }
.difficulty-label { font-size: 10.5px; color: var(--t-faint, #BBBDC4); }
.focus-tags { display: flex; flex-wrap: wrap; gap: 4px; }
.focus-tag {
  font-size: 10px; font-weight: 600;
  padding: 2px 7px; border-radius: 20px;
  background: rgba(99,102,241,0.08); color: #6366F1;
}

.ev-start-bar {
  display: flex; align-items: center; gap: 14px;
  margin-bottom: 40px;
}
.btn-start {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 12px 28px; border-radius: 10px;
  background: #6366F1; color: #fff;
  font-size: 14px; font-weight: 700; border: none; cursor: pointer;
  transition: background 0.15s;
}
.btn-start:hover:not(:disabled) { background: #4F46E5; }
.btn-start:disabled { opacity: 0.6; cursor: not-allowed; }
.start-hint { font-size: 12.5px; color: var(--t-muted, #8B8D99); }

/* Past sessions */
.past-sessions { }
.ps-title { font-size: 14px; font-weight: 700; color: var(--t-muted); margin: 0 0 12px; }
.ps-list { display: flex; flex-direction: column; gap: 6px; }
.ps-item {
  display: flex; align-items: center; justify-content: space-between;
  background: #fff; border-radius: 10px;
  border: 1px solid var(--border, rgba(0,0,0,0.07));
  padding: 12px 16px; cursor: pointer; transition: box-shadow 0.15s;
}
.ps-item:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.ps-meta { display: flex; align-items: center; gap: 10px; }
.ps-date { font-size: 12.5px; color: var(--t-muted); }
.ps-status { font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 20px; }
.ps-status.completed { background: rgba(34,197,94,0.1); color: #22C55E; }
.ps-status.in-progress { background: rgba(249,115,22,0.1); color: #F97316; }
.ps-score { display: flex; align-items: baseline; gap: 2px; }
.ps-score-num { font-size: 22px; font-weight: 800; }
.ps-score-num.green { color: #22C55E; }
.ps-score-num.orange { color: #F97316; }
.ps-score-num.red { color: #EF4444; }
.ps-score-label { font-size: 12px; color: var(--t-muted); }

/* ── Chat phase ───────────────────────────────── */
.ev-chat-phase {
  height: calc(100vh - 56px);
  overflow: hidden;
}
.ev-chat-layout {
  display: flex;
  height: 100%;
}
.ev-persona-panel {
  width: 200px; flex-shrink: 0;
  border-right: 1px solid var(--border, rgba(0,0,0,0.07));
  padding: 24px 18px;
  display: flex; flex-direction: column; gap: 8px;
  background: var(--bg-card, #fff);
}
.ep-avatar { font-size: 40px; line-height: 1; }
.ep-name { font-size: 16px; font-weight: 800; color: var(--t-primary, #0F0F13); }
.ep-role { font-size: 11.5px; font-weight: 700; color: #6366F1; }
.ep-desc { font-size: 11.5px; color: var(--t-muted, #8B8D99); line-height: 1.5; }
.ep-focus-areas { margin-top: 8px; }
.ep-fa-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: var(--t-faint); margin-bottom: 5px; }
.ep-fa-tag {
  display: inline-block;
  font-size: 10px; font-weight: 600;
  padding: 2px 7px; border-radius: 20px;
  background: rgba(99,102,241,0.08); color: #6366F1;
  margin: 0 3px 3px 0;
}
.btn-end-session {
  margin-top: auto;
  padding: 8px 0; border-radius: 8px;
  border: 1.5px solid var(--border, rgba(0,0,0,0.12));
  background: transparent; color: var(--t-muted);
  font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.15s;
}
.btn-end-session:hover { background: rgba(239,68,68,0.05); border-color: rgba(239,68,68,0.3); color: #DC2626; }

.ev-chat-area {
  flex: 1; display: flex; flex-direction: column; overflow: hidden;
}
.ev-messages {
  flex: 1; overflow-y: auto;
  padding: 24px 28px;
  display: flex; flex-direction: column; gap: 16px;
}
.ev-message {
  display: flex; align-items: flex-end; gap: 10px;
}
.ev-message.user { flex-direction: row-reverse; }
.msg-avatar {
  width: 32px; height: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; flex-shrink: 0;
}
.msg-avatar.evaluator { background: rgba(99,102,241,0.1); }
.msg-avatar.user { background: #6366F1; color: #fff; font-size: 11px; font-weight: 700; }
.msg-bubble {
  max-width: 70%; padding: 12px 16px; border-radius: 16px;
  font-size: 14px; line-height: 1.6;
}
.msg-bubble.evaluator {
  background: #fff;
  border: 1px solid var(--border, rgba(0,0,0,0.07));
  border-bottom-left-radius: 4px;
  color: var(--t-primary, #0F0F13);
}
.msg-bubble.user {
  background: #6366F1; color: #fff;
  border-bottom-right-radius: 4px;
}
.msg-bubble.typing {
  display: flex; align-items: center; gap: 4px; padding: 14px 18px;
}
.dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--t-muted, #8B8D99);
  animation: bounce 1.2s infinite;
}
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-5px); }
}

.ev-input-area {
  border-top: 1px solid var(--border, rgba(0,0,0,0.07));
  padding: 14px 20px;
  background: var(--bg-card, #fff);
}
.ev-input-row { display: flex; gap: 10px; align-items: flex-end; }
.ev-textarea {
  flex: 1; min-height: 64px; max-height: 120px;
  border: 1.5px solid var(--border, rgba(0,0,0,0.12));
  border-radius: 10px; padding: 10px 14px;
  font-size: 13.5px; font-family: inherit; resize: vertical;
  color: var(--t-primary, #0F0F13); background: var(--bg-content, #F5F5F7);
  transition: border-color 0.15s;
}
.ev-textarea:focus { outline: none; border-color: #6366F1; background: #fff; }
.ev-textarea:disabled { opacity: 0.6; }
.btn-send {
  width: 40px; height: 40px; border-radius: 10px;
  background: #6366F1; color: #fff;
  border: none; cursor: pointer; transition: background 0.15s;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.btn-send:hover:not(:disabled) { background: #4F46E5; }
.btn-send:disabled { opacity: 0.5; cursor: not-allowed; }
.ev-input-hint { font-size: 11.5px; color: var(--t-faint, #BBBDC4); margin-top: 6px; }

/* Score summary */
.ev-score-summary {
  border-top: 1px solid var(--border, rgba(0,0,0,0.07));
  padding: 28px 32px;
  text-align: center;
  background: var(--bg-card, #fff);
}
.ess-title { font-size: 16px; font-weight: 800; margin-bottom: 16px; }
.ess-score-row { display: flex; align-items: center; justify-content: center; gap: 12px; margin-bottom: 12px; }
.ess-score { font-size: 52px; font-weight: 800; }
.ess-score.green { color: #22C55E; }
.ess-score.orange { color: #F97316; }
.ess-score.red { color: #EF4444; }
.ess-score-label { font-size: 14px; color: var(--t-muted); }
.ess-feedback { font-size: 13.5px; color: var(--t-muted); line-height: 1.7; max-width: 480px; margin: 0 auto 20px; }
.ess-actions { display: flex; justify-content: center; gap: 10px; }

/* Shared buttons */
.btn-primary {
  padding: 9px 20px; border-radius: 8px;
  background: #6366F1; color: #fff;
  font-size: 13px; font-weight: 700; border: none; cursor: pointer;
  transition: background 0.15s;
}
.btn-primary:hover { background: #4F46E5; }
.btn-outline {
  padding: 9px 20px; border-radius: 8px;
  border: 1.5px solid var(--border, rgba(0,0,0,0.12));
  background: transparent; color: var(--t-primary, #0F0F13);
  font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.15s;
}
.btn-outline:hover { background: var(--bg-content, #F5F5F7); }

/* Spin */
.spin { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Colors */
.green { color: #22C55E; }
.orange { color: #F97316; }
.red { color: #EF4444; }
</style>
