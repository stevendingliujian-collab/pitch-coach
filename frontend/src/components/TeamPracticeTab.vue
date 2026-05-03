<template>
  <div class="team-tab">
    <!-- Header -->
    <div class="team-header">
      <div class="team-header-text">
        <h3 class="team-title">多人组队排练</h3>
        <p class="team-desc">将述标任务拆分为多个角色，团队成员各自练习后汇总评分</p>
      </div>
      <button class="btn-create" @click="showCreate = true">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="7" y1="2" x2="7" y2="12"/><line x1="2" y1="7" x2="12" y2="7"/>
        </svg>
        创建会话
      </button>
    </div>

    <!-- Sessions list -->
    <div v-if="loading" class="team-loading">加载中…</div>
    <div v-else-if="!sessions.length" class="team-empty">
      <svg width="40" height="40" viewBox="0 0 40 40" fill="none" stroke="currentColor" stroke-width="1.5" style="opacity:.3">
        <circle cx="20" cy="20" r="17"/>
        <path d="M13 20h14M20 13v14"/>
      </svg>
      <p>暂无组队排练会话，创建一个吧</p>
    </div>
    <div v-else class="sessions-list">
      <div
        v-for="s in sessions"
        :key="s.id"
        class="session-card"
        @click="openSession(s.id)"
      >
        <div class="sc-head">
          <div class="sc-title">{{ s.title }}</div>
          <span class="sc-status" :class="`status-${s.status}`">{{ statusLabel(s.status) }}</span>
        </div>
        <div class="sc-meta">
          <span>{{ s.roles.length }} 个角色</span>
          <span v-if="s.avg_score !== null">平均 {{ s.avg_score }} 分</span>
          <span>{{ formatDate(s.created_at) }}</span>
        </div>
        <div class="sc-roles">
          <span v-for="(r, i) in s.roles" :key="i" class="sc-role-chip">{{ r.role }}</span>
        </div>
      </div>
    </div>

    <!-- Session detail modal -->
    <Transition name="modal">
      <div v-if="activeSession" class="modal-overlay" @click.self="activeSession = null">
        <div class="modal-box">
          <div class="modal-head">
            <span class="modal-title">{{ activeSession.title }}</span>
            <button class="modal-close" @click="activeSession = null">✕</button>
          </div>

          <p v-if="activeSession.description" class="modal-desc">{{ activeSession.description }}</p>

          <!-- Roles + Participants grid -->
          <div class="roles-grid">
            <div
              v-for="(role, i) in activeSession.roles"
              :key="i"
              class="role-card"
            >
              <div class="rc-idx">角色 {{ i + 1 }}</div>
              <div class="rc-name">{{ role.role }}</div>
              <div class="rc-desc">{{ role.description }}</div>
              <div class="rc-time">目标 {{ role.suggested_duration_sec }}s</div>

              <!-- Participant for this role -->
              <div v-if="participantFor(i)" class="rc-participant">
                <span class="rcp-name">用户 #{{ participantFor(i)!.user_id }}</span>
                <span class="rcp-status" :class="participantFor(i)!.status === 1 ? 'submitted' : 'pending'">
                  {{ participantFor(i)!.status === 1 ? '已提交' : '待提交' }}
                </span>
                <span v-if="participantFor(i)!.score !== null" class="rcp-score">{{ participantFor(i)!.score }} 分</span>
              </div>
              <button
                v-else-if="activeSession.status === 1"
                class="btn-join"
                @click="joinRole(activeSession.id, i)"
              >认领角色</button>
              <span v-else class="rc-empty">空缺</span>
            </div>
          </div>

          <!-- Session footer -->
          <div class="modal-footer">
            <div v-if="activeSession.avg_score !== null" class="session-score">
              综合得分：<strong>{{ activeSession.avg_score }}</strong> 分
            </div>
            <div class="modal-actions">
              <button
                v-if="activeSession.status === 2"
                class="btn-complete"
                @click="completeSession(activeSession.id)"
              >标记完成</button>
              <span v-else-if="activeSession.status === 3" class="status-done">✓ 已完成</span>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Create session dialog -->
    <Transition name="modal">
      <div v-if="showCreate" class="modal-overlay" @click.self="showCreate = false">
        <div class="modal-box create-box">
          <div class="modal-head">
            <span class="modal-title">创建组队排练会话</span>
            <button class="modal-close" @click="showCreate = false">✕</button>
          </div>

          <div class="form-group">
            <label>会话标题</label>
            <input v-model="form.title" class="form-input" placeholder="如：Q2大标模拟排练"/>
          </div>
          <div class="form-group">
            <label>说明（可选）</label>
            <input v-model="form.description" class="form-input" placeholder="简要描述会话目的"/>
          </div>

          <div class="roles-editor">
            <div class="re-header">
              <span>角色分工</span>
              <button class="btn-add-role" @click="addRole" :disabled="form.roles.length >= 6">＋ 添加角色</button>
            </div>
            <div v-for="(r, i) in form.roles" :key="i" class="role-row">
              <input v-model="r.role" class="role-input-name" :placeholder="`角色 ${i + 1} 名称`"/>
              <input v-model="r.description" class="role-input-desc" placeholder="负责内容描述"/>
              <input v-model.number="r.suggested_duration_sec" class="role-input-dur" type="number" min="30" max="600" placeholder="秒"/>
              <button class="btn-rm-role" @click="removeRole(i)" :disabled="form.roles.length <= 2">✕</button>
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn-cancel" @click="showCreate = false">取消</button>
            <button class="btn-submit" @click="submitCreate" :disabled="!form.title || creating">
              {{ creating ? '创建中…' : '创建会话' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { teamPracticeApi, type TeamSession, type TeamParticipant } from '@/api/teamPractice'

const props = defineProps<{ taskId: number }>()

const loading = ref(true)
const sessions = ref<TeamSession[]>([])
const activeSession = ref<TeamSession | null>(null)
const showCreate = ref(false)
const creating = ref(false)

const form = ref({
  title: '',
  description: '',
  roles: [
    { role: '开场与公司介绍', description: '自我介绍 + 公司简介 + 方案亮点预告', suggested_duration_sec: 120 },
    { role: '方案详细讲解', description: '核心解决方案、技术方案、实施计划', suggested_duration_sec: 300 },
    { role: '案例与ROI', description: '成功案例 + 投资回报分析 + 承诺与保障', suggested_duration_sec: 180 },
  ],
})

onMounted(loadSessions)

async function loadSessions() {
  loading.value = true
  try {
    const res = await teamPracticeApi.listSessions(props.taskId)
    sessions.value = res.data
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

async function openSession(id: number) {
  try {
    const res = await teamPracticeApi.getSession(id)
    activeSession.value = res.data
  } catch {
    ElMessage.error('加载会话失败')
  }
}

function participantFor(roleIndex: number): TeamParticipant | undefined {
  return activeSession.value?.participants?.find(p => p.role_index === roleIndex)
}

async function joinRole(sessionId: number, roleIndex: number) {
  try {
    await teamPracticeApi.join(sessionId, roleIndex)
    ElMessage.success('已认领角色')
    const res = await teamPracticeApi.getSession(sessionId)
    activeSession.value = res.data
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? '认领失败')
  }
}

async function completeSession(sessionId: number) {
  try {
    const res = await teamPracticeApi.complete(sessionId)
    activeSession.value = res.data
    ElMessage.success('会话已标记完成')
    loadSessions()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? '操作失败')
  }
}

function addRole() {
  if (form.value.roles.length < 6) {
    form.value.roles.push({ role: '', description: '', suggested_duration_sec: 120 })
  }
}

function removeRole(i: number) {
  if (form.value.roles.length > 2) {
    form.value.roles.splice(i, 1)
  }
}

async function submitCreate() {
  if (!form.value.title) return
  if (form.value.roles.some(r => !r.role)) {
    ElMessage.warning('请填写所有角色名称')
    return
  }
  creating.value = true
  try {
    await teamPracticeApi.createSession({
      pitch_task_id: props.taskId,
      title: form.value.title,
      description: form.value.description || undefined,
      roles: form.value.roles,
    })
    ElMessage.success('会话创建成功')
    showCreate.value = false
    form.value = {
      title: '', description: '',
      roles: [
        { role: '开场与公司介绍', description: '自我介绍 + 公司简介 + 方案亮点预告', suggested_duration_sec: 120 },
        { role: '方案详细讲解', description: '核心解决方案、技术方案、实施计划', suggested_duration_sec: 300 },
        { role: '案例与ROI', description: '成功案例 + 投资回报分析 + 承诺与保障', suggested_duration_sec: 180 },
      ],
    }
    loadSessions()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? '创建失败')
  } finally {
    creating.value = false
  }
}

function statusLabel(status: number) {
  return ['草稿', '开放认领', '进行中', '已完成'][status] ?? '未知'
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.team-tab { padding: 20px 24px; }

.team-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: 20px; gap: 16px;
}
.team-title { font-size: 16px; font-weight: 700; color: rgba(255,255,255,0.9); margin: 0 0 4px; }
.team-desc { font-size: 12.5px; color: rgba(255,255,255,0.4); margin: 0; }

.btn-create {
  display: flex; align-items: center; gap: 6px;
  padding: 7px 14px; border-radius: 8px; border: none;
  background: var(--accent); color: #fff; font-size: 13px; font-weight: 600;
  cursor: pointer; flex-shrink: 0; transition: opacity 0.15s;
}
.btn-create:hover { opacity: 0.85; }

.team-loading, .team-empty {
  text-align: center; color: rgba(255,255,255,0.3); padding: 40px;
  font-size: 13px;
}
.team-empty p { margin: 12px 0 0; }

/* Sessions list */
.sessions-list { display: flex; flex-direction: column; gap: 10px; }
.session-card {
  background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.07);
  border-radius: 10px; padding: 14px 16px;
  cursor: pointer; transition: background 0.15s;
}
.session-card:hover { background: rgba(255,255,255,0.07); }
.sc-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.sc-title { font-size: 14px; font-weight: 600; color: rgba(255,255,255,0.85); }
.sc-status {
  font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 10px;
}
.status-0 { background: rgba(107,114,128,0.15); color: #9ca3af; }
.status-1 { background: rgba(99,102,241,0.15); color: #818CF8; }
.status-2 { background: rgba(249,115,22,0.15); color: #F97316; }
.status-3 { background: rgba(34,197,94,0.15); color: #22C55E; }

.sc-meta { font-size: 11px; color: rgba(255,255,255,0.3); display: flex; gap: 12px; margin-bottom: 8px; }
.sc-roles { display: flex; flex-wrap: wrap; gap: 6px; }
.sc-role-chip {
  font-size: 11px; padding: 2px 8px; border-radius: 10px;
  background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.5);
}

/* Modal */
.modal-overlay {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0,0,0,0.6); backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center;
  padding: 24px;
}
.modal-box {
  background: #1C1C2A; border: 1px solid rgba(255,255,255,0.1);
  border-radius: 16px; width: 100%; max-width: 680px;
  max-height: 80vh; overflow-y: auto;
  padding: 24px; box-shadow: 0 16px 64px rgba(0,0,0,0.5);
}
.modal-head {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 14px;
}
.modal-title { font-size: 16px; font-weight: 700; color: rgba(255,255,255,0.9); }
.modal-close {
  width: 28px; height: 28px; border-radius: 6px; border: none;
  background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.4);
  cursor: pointer; font-size: 12px;
}
.modal-desc { font-size: 13px; color: rgba(255,255,255,0.4); margin: 0 0 16px; }

/* Roles grid */
.roles-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 10px; margin-bottom: 16px; }
.role-card {
  background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.07);
  border-radius: 10px; padding: 12px;
}
.rc-idx { font-size: 10px; color: rgba(255,255,255,0.3); margin-bottom: 4px; }
.rc-name { font-size: 13px; font-weight: 700; color: rgba(255,255,255,0.85); margin-bottom: 4px; }
.rc-desc { font-size: 11px; color: rgba(255,255,255,0.4); margin-bottom: 6px; line-height: 1.4; }
.rc-time { font-size: 10px; color: rgba(255,255,255,0.25); margin-bottom: 8px; }

.rc-participant { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.rcp-name { font-size: 11px; color: rgba(255,255,255,0.55); }
.rcp-status { font-size: 10px; font-weight: 700; padding: 1px 6px; border-radius: 8px; }
.rcp-status.submitted { background: rgba(34,197,94,0.15); color: #22C55E; }
.rcp-status.pending { background: rgba(249,115,22,0.12); color: #F97316; }
.rcp-score { font-size: 11px; font-weight: 700; color: #6366F1; }

.btn-join {
  width: 100%; padding: 6px; border-radius: 6px; border: 1px dashed rgba(99,102,241,0.4);
  background: rgba(99,102,241,0.06); color: #818CF8; font-size: 11px; font-weight: 600;
  cursor: pointer; transition: background 0.15s;
}
.btn-join:hover { background: rgba(99,102,241,0.12); }
.rc-empty { font-size: 11px; color: rgba(255,255,255,0.2); }

.modal-footer {
  display: flex; justify-content: space-between; align-items: center;
  border-top: 1px solid rgba(255,255,255,0.06); padding-top: 14px; margin-top: 4px;
}
.session-score { font-size: 14px; color: rgba(255,255,255,0.7); }
.session-score strong { color: #6366F1; font-size: 20px; }
.modal-actions { display: flex; gap: 10px; margin-left: auto; }
.btn-complete {
  padding: 7px 16px; border-radius: 8px; border: none;
  background: var(--accent); color: #fff; font-size: 13px; font-weight: 600;
  cursor: pointer; transition: opacity 0.15s;
}
.btn-complete:hover { opacity: 0.85; }
.status-done { font-size: 13px; font-weight: 700; color: #22C55E; }

/* Create form */
.create-box { max-width: 560px; }
.form-group { margin-bottom: 12px; }
.form-group label { font-size: 12px; font-weight: 600; color: rgba(255,255,255,0.5); display: block; margin-bottom: 6px; }
.form-input {
  width: 100%; padding: 8px 12px; border-radius: 8px;
  background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1);
  color: rgba(255,255,255,0.85); font-size: 13px; outline: none;
  box-sizing: border-box;
}
.form-input:focus { border-color: rgba(99,102,241,0.5); }

.roles-editor { margin-bottom: 16px; }
.re-header {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 12px; font-weight: 600; color: rgba(255,255,255,0.5); margin-bottom: 8px;
}
.btn-add-role {
  font-size: 12px; color: #818CF8; background: none; border: none; cursor: pointer;
}
.btn-add-role:disabled { opacity: 0.4; cursor: not-allowed; }
.role-row {
  display: grid; grid-template-columns: 1fr 1.5fr 60px 28px;
  gap: 8px; margin-bottom: 8px; align-items: center;
}
.role-input-name, .role-input-desc, .role-input-dur {
  padding: 7px 10px; border-radius: 7px;
  background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
  color: rgba(255,255,255,0.85); font-size: 12px; outline: none; width: 100%;
  box-sizing: border-box;
}
.btn-rm-role {
  width: 28px; height: 28px; border-radius: 6px; border: none;
  background: rgba(239,68,68,0.1); color: #EF4444; cursor: pointer; font-size: 11px;
}
.btn-rm-role:disabled { opacity: 0.3; cursor: not-allowed; }

.btn-cancel {
  padding: 7px 16px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1);
  background: none; color: rgba(255,255,255,0.5); font-size: 13px; cursor: pointer;
}
.btn-submit {
  padding: 7px 16px; border-radius: 8px; border: none;
  background: var(--accent); color: #fff; font-size: 13px; font-weight: 600; cursor: pointer;
}
.btn-submit:disabled { opacity: 0.5; cursor: not-allowed; }

/* Transition */
.modal-enter-active, .modal-leave-active { transition: opacity 0.2s, transform 0.2s; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-box { transition: transform 0.2s; }
.modal-enter-from .modal-box, .modal-leave-to .modal-box { transform: translateY(12px); }
</style>
