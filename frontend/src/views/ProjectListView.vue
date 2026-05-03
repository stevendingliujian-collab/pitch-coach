<template>
  <div class="v2-page">
    <!-- Topbar -->
    <div class="v2-topbar">
      <span class="v2-topbar-title">我的项目</span>
      <div class="v2-topbar-flex" />
      <button class="btn-v2 btn-v2-ghost" @click="showImport = true">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M7 1v8M3 6l4 4 4-4"/><rect x="1" y="11" width="12" height="2" rx="1"/>
        </svg>
        导入 PPT
      </button>
      <button class="btn-v2 btn-v2-primary" @click="showCreate = true">
        <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" stroke-width="2.2">
          <line x1="6.5" y1="1" x2="6.5" y2="12"/><line x1="1" y1="6.5" x2="12" y2="6.5"/>
        </svg>
        新建项目
      </button>
    </div>

    <div class="v2-content">
      <!-- Stats row -->
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-label">项目总数 <span class="stat-dot" style="background:var(--accent)"/></div>
          <div class="stat-num">{{ tasks.length }}</div>
          <div class="stat-trend up">
            <svg width="11" height="11" viewBox="0 0 11 11" fill="currentColor"><path d="M5.5 2L10 7H1z"/></svg>
            本月新增 {{ recentCount }} 个
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">累计排练 <span class="stat-dot" style="background:var(--green)"/></div>
          <div class="stat-num">{{ totalRehearsals }}</div>
          <div class="stat-trend up">
            <svg width="11" height="11" viewBox="0 0 11 11" fill="currentColor"><path d="M5.5 2L10 7H1z"/></svg>
            较上月 +6 次
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">平均得分 <span class="stat-dot" style="background:var(--orange)"/></div>
          <div class="stat-num">{{ avgScore }}</div>
          <div class="stat-trend up">
            <svg width="11" height="11" viewBox="0 0 11 11" fill="currentColor"><path d="M5.5 2L10 7H1z"/></svg>
            较上次 +4 分
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">连续打卡 <span class="stat-dot" style="background:var(--red)"/></div>
          <div class="stat-num">{{ streak }}</div>
          <div class="stat-trend fire">🔥 天连击</div>
        </div>
      </div>

      <!-- Project list header -->
      <div class="section-header">
        <span class="section-title">项目列表</span>
        <a class="section-link" @click.prevent>全部 →</a>
      </div>

      <!-- Loading skeleton -->
      <div v-if="loading" class="project-grid">
        <div v-for="n in 3" :key="n" class="project-card skeleton" />
      </div>

      <!-- Empty state -->
      <div v-else-if="tasks.length === 0" class="empty-state">
        <div class="empty-icon">
          <svg width="40" height="40" viewBox="0 0 40 40" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
            <rect x="5" y="5" width="30" height="30" rx="4"/><line x1="20" y1="13" x2="20" y2="27"/><line x1="13" y1="20" x2="27" y2="20"/>
          </svg>
        </div>
        <div class="empty-text">还没有项目</div>
        <div class="empty-sub">上传 PPT，创建你的第一个述标项目</div>
        <button class="btn-v2 btn-v2-primary" style="margin-top:16px" @click="showCreate = true">新建项目</button>
      </div>

      <!-- Project cards grid -->
      <div v-else class="project-grid">
        <div
          v-for="task in tasks"
          :key="task.id"
          class="project-card"
          @click="router.push(`/projects/${task.id}`)"
        >
          <!-- Status + ring -->
          <div class="card-header">
            <div class="card-status">
              <span v-if="task.result" :class="['result-badge', resultClass(task.result)]">
                {{ resultText(task.result) }}
              </span>
              <template v-else>
                <span class="status-dot" :class="statusDotClass(task)" />
                <span class="status-label">{{ statusLabel(task) }}</span>
              </template>
            </div>
            <!-- SVG readiness ring -->
            <div class="readiness-ring">
              <svg width="44" height="44" viewBox="0 0 44 44">
                <circle cx="22" cy="22" r="17" fill="none" stroke="#E5E7EB" stroke-width="3"/>
                <circle
                  cx="22" cy="22" r="17"
                  fill="none"
                  :stroke="ringColor(task)"
                  stroke-width="3"
                  stroke-linecap="round"
                  :stroke-dasharray="`${2 * Math.PI * 17}`"
                  :stroke-dashoffset="`${2 * Math.PI * 17 * (1 - readiness(task) / 100)}`"
                  transform="rotate(-90 22 22)"
                  style="transition: stroke-dashoffset 0.6s ease;"
                />
              </svg>
              <span class="ring-num">{{ readiness(task) }}</span>
            </div>
          </div>

          <div class="card-name">{{ task.name }}</div>
          <div class="card-meta">
            <span v-if="task.page_count">{{ task.page_count }} 页 PPT</span>
            <span v-if="task.page_count && task.bid_date">·</span>
            <span v-if="task.bid_date">{{ daysLeftShort(task.bid_date) }}</span>
            <span v-if="!task.page_count && !task.bid_date">刚创建</span>
          </div>

          <div class="card-footer">
            <span class="card-rehearsal-count">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.8">
                <circle cx="6" cy="6" r="4.5"/><polyline points="6 3.5 6 6 7.5 7.5"/>
              </svg>
              {{ task.rehearsal_count ?? 0 }} 次排练
            </span>
            <div class="card-actions">
              <button class="card-btn" title="开始排练" @click.stop="router.push(`/projects/${task.id}`)">
                <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8">
                  <circle cx="10" cy="10" r="7.5"/><polygon points="8 7 14 10 8 13" fill="currentColor" stroke="none"/>
                </svg>
              </button>
              <button class="card-btn" title="讲解方案" @click.stop="router.push(`/projects/${task.id}`)">
                <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8">
                  <rect x="3" y="2" width="14" height="16" rx="1.5"/>
                  <line x1="7" y1="7" x2="13" y2="7"/>
                  <line x1="7" y1="11" x2="11" y2="11"/>
                </svg>
              </button>
            </div>
          </div>
        </div>

        <!-- Add card -->
        <div class="project-card add-card" @click="showCreate = true">
          <div class="add-icon">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="currentColor" stroke-width="1.8">
              <line x1="14" y1="5" x2="14" y2="23"/><line x1="5" y1="14" x2="23" y2="14"/>
            </svg>
          </div>
          <div class="add-label">上传 PPT，创建项目</div>
          <div class="add-sub">支持 PPTX / PDF</div>
        </div>
      </div>
    </div>

    <!-- Create project dialog — custom styled -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showCreate" class="modal-backdrop" @mousedown.self="showCreate = false">
          <div class="modal-card">
            <!-- Header -->
            <div class="modal-header">
              <div class="modal-header-left">
                <div class="modal-icon">
                  <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8">
                    <rect x="2" y="3" width="7" height="8" rx="1.5"/>
                    <rect x="11" y="3" width="7" height="4" rx="1.5"/>
                    <rect x="11" y="9" width="7" height="8" rx="1.5"/>
                    <rect x="2" y="13" width="7" height="4" rx="1.5"/>
                  </svg>
                </div>
                <div>
                  <div class="modal-title">新建项目</div>
                  <div class="modal-subtitle">填写述标项目基本信息</div>
                </div>
              </div>
              <button class="modal-close" @click="showCreate = false">
                <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="3" y1="3" x2="13" y2="13"/><line x1="13" y1="3" x2="3" y2="13"/>
                </svg>
              </button>
            </div>

            <!-- Body -->
            <div class="modal-body">
              <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-position="top" class="v2-form">
                <el-form-item label="项目名称" prop="name" class="v2-form-item required">
                  <el-input v-model="createForm.name" placeholder="如：苏州XX公司 MES 系统项目" class="v2-input" />
                </el-form-item>

                <div class="form-row">
                  <el-form-item label="客户名称" class="v2-form-item">
                    <el-input v-model="createForm.customer_name" placeholder="客户公司名称" class="v2-input" />
                  </el-form-item>
                  <el-form-item label="客户行业" class="v2-form-item">
                    <el-select v-model="createForm.customer_industry" placeholder="选择行业" class="v2-select">
                      <el-option v-for="i in INDUSTRIES" :key="i" :label="i" :value="i" />
                    </el-select>
                  </el-form-item>
                </div>

                <div class="form-row">
                  <el-form-item label="述标日期" class="v2-form-item">
                    <el-date-picker v-model="createForm.bid_date" type="date" value-format="YYYY-MM-DD"
                      placeholder="选择日期" style="width:100%" class="v2-input" />
                  </el-form-item>
                  <el-form-item label="述标时长（分钟）" class="v2-form-item">
                    <el-input-number v-model="createForm.bid_time_limit" :min="5" :max="120"
                      style="width:100%" class="v2-input" />
                  </el-form-item>
                </div>

                <el-form-item class="v2-form-item">
                  <template #label>
                    <span>招标要求摘要</span>
                    <span class="optional-tag">选填</span>
                  </template>
                  <el-input v-model="createForm.bid_requirements" type="textarea" :rows="3"
                    placeholder="粘贴评分标准、技术要求、注意事项等，AI 生成方案时会参考" class="v2-input" />
                </el-form-item>
              </el-form>
            </div>

            <!-- Footer -->
            <div class="modal-footer">
              <button class="modal-btn-cancel" @click="showCreate = false">取消</button>
              <button class="modal-btn-primary" :disabled="creating" @click="handleCreate">
                <svg v-if="creating" class="spin-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
                </svg>
                {{ creating ? '创建中…' : '创建项目' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Import PPT hint modal V2 -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showImport" class="modal-backdrop" @mousedown.self="showImport = false">
          <div class="modal-card import-card">
            <div class="modal-header">
              <div class="modal-icon import-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                  <line x1="12" y1="18" x2="12" y2="12"/>
                  <line x1="9" y1="15" x2="15" y2="15"/>
                </svg>
              </div>
              <div>
                <div class="modal-title">导入 PPT</div>
                <div class="modal-subtitle">上传述标演示文稿</div>
              </div>
              <button class="modal-close" @click="showImport = false">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="1" y1="1" x2="13" y2="13"/><line x1="13" y1="1" x2="1" y2="13"/>
                </svg>
              </button>
            </div>
            <div class="import-body">
              <div class="import-step">
                <div class="step-num">1</div>
                <div>先创建项目（填写客户名、行业、述标日期）</div>
              </div>
              <div class="import-step">
                <div class="step-num">2</div>
                <div>进入项目详情页，点击「上传 PPT」上传文件</div>
              </div>
              <div class="import-step">
                <div class="step-num">3</div>
                <div>AI 自动解析并生成逐页讲解方案（约30秒）</div>
              </div>
            </div>
            <div class="modal-footer">
              <button class="btn-v2" @click="showImport = false">取消</button>
              <button class="btn-v2 btn-v2-primary" @click="showImport = false; showCreate = true">
                <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="6.5" y1="1" x2="6.5" y2="12"/><line x1="1" y1="6.5" x2="12" y2="6.5"/>
                </svg>
                创建项目
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { pitchTaskApi, type PitchTask } from '@/api/pitchTask'
import { dashboardApi } from '@/api/dashboard'
import { gamificationApi } from '@/api/gamification'
import dayjs from 'dayjs'
import { useConversion } from '@/composables/useConversion'

const router = useRouter()
const { checkTrigger } = useConversion()
const tasks = ref<PitchTask[]>([])
const loading = ref(false)
const showCreate = ref(false)
const showImport = ref(false)
const creating = ref(false)
const createFormRef = ref<FormInstance>()
const avgScoreReal = ref<number | null>(null)
const streakReal = ref<number>(0)

const INDUSTRIES = ['非标自动化', '系统集成', '软件开发', '信息化', '工业互联网', '其他']

const createForm = ref({
  name: '', customer_name: '', customer_industry: '',
  bid_date: '', bid_time_limit: 30, bid_requirements: '',
})
const createRules: FormRules = {
  name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
}

// Stats — real data from APIs
const recentCount     = computed(() => tasks.value.filter(t => dayjs(t.created_at).isAfter(dayjs().startOf('month'))).length)
const totalRehearsals = computed(() => tasks.value.reduce((s, t) => s + (t.rehearsal_count ?? 0), 0))
const avgScore  = computed(() => avgScoreReal.value ?? '—')
const streak    = computed(() => streakReal.value)

onMounted(async () => {
  loading.value = true
  const [tasksRes, overviewRes, streakRes] = await Promise.allSettled([
    pitchTaskApi.list(),
    dashboardApi.getOverview(),
    gamificationApi.streak(),
  ])
  if (tasksRes.status === 'fulfilled') tasks.value = tasksRes.value.data
  if (overviewRes.status === 'fulfilled') avgScoreReal.value = overviewRes.value.data.avg_score
  if (streakRes.status === 'fulfilled') streakReal.value = streakRes.value.data.current_streak
  loading.value = false
})

async function handleCreate() {
  await createFormRef.value?.validate()
  creating.value = true
  try {
    const payload = { ...createForm.value, bid_date: createForm.value.bid_date || undefined }
    const res = await pitchTaskApi.create(payload)
    tasks.value.unshift(res.data)
    showCreate.value = false
    if (payload.bid_date) {
      const diff = dayjs(payload.bid_date).diff(dayjs(), 'day')
      if (diff >= 0 && diff <= 7) checkTrigger('T9', { days_left: diff, task_id: res.data.id })
    }
    router.push(`/projects/${res.data.id}`)
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}

function readiness(task: PitchTask): number {
  // Use real readiness_score from API (computed from rehearsal count + best score)
  if (task.readiness_score != null) return task.readiness_score
  // Fallback: derive from rehearsal count only
  const r = task.rehearsal_count ?? 0
  if (r === 0) return 0
  return Math.min(40 + r * 12, 98)
}

function ringColor(task: PitchTask): string {
  const r = readiness(task)
  if (r === 0) return '#E5E7EB'
  if (r >= 80) return '#22C55E'
  if (r >= 50) return '#F59E0B'
  return '#EF4444'
}

function statusLabel(task: PitchTask): string {
  if ((task as any).status === 'generating') return '方案生成中'
  if ((task.rehearsal_count ?? 0) > 0) return '排练中'
  if (task.bid_date && dayjs(task.bid_date).diff(dayjs(), 'day') <= 7) return '述标就绪'
  return '准备中'
}

function statusDotClass(task: PitchTask): string {
  if ((task as any).status === 'generating') return 'amber'
  if ((task.rehearsal_count ?? 0) > 0) return 'blue'
  return 'green'
}

function resultText(result: number): string {
  return { 1: '中标 ✅', 2: '未中标 ❌', 3: '弃标', 4: '流标' }[result] ?? ''
}

function resultClass(result: number): string {
  return { 1: 'won', 2: 'lost', 3: 'withdrawn', 4: 'void' }[result] ?? ''
}

function daysLeftShort(bidDate: string): string {
  const diff = dayjs(bidDate).diff(dayjs(), 'day')
  if (diff < 0) return '已过期'
  if (diff === 0) return '今天述标'
  return `距述标 ${diff} 天`
}
</script>

<style scoped>
/* Section header */
.section-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 16px;
}
.section-title { font-size: 14px; font-weight: 700; color: var(--t-primary); }
.section-link  { font-size: 13px; color: var(--t-muted); cursor: pointer; text-decoration: none; }
.section-link:hover { color: var(--accent); }

/* Project grid */
.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}

/* Project card */
.project-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-light);
  box-shadow: var(--shadow-md);
  padding: 18px;
  cursor: pointer;
  transition: transform 0.18s, box-shadow 0.18s;
}
.project-card:hover:not(.add-card) {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

/* Card header: status + ring */
.card-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: 12px;
}
.card-status { display: flex; align-items: center; gap: 6px; }
.status-dot {
  width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0;
}
.status-dot.green { background: #22C55E; }
.status-dot.blue  { background: #6366F1; }
.status-dot.amber { background: #F59E0B; }
.status-label { font-size: 12px; font-weight: 600; color: var(--t-muted); }

/* Result badge */
.result-badge { padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 700; }
.result-badge.won        { background: #DCFCE7; color: #16a34a; }
.result-badge.lost       { background: #FEE2E2; color: #DC2626; }
.result-badge.withdrawn  { background: #F3F4F6; color: #6b7280; }
.result-badge.void       { background: #FEF3C7; color: #92400E; }

/* Readiness ring */
.readiness-ring {
  position: relative;
  width: 44px; height: 44px;
}
.ring-num {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 800; color: var(--t-primary);
}

/* Card body */
.card-name {
  font-size: 15px; font-weight: 700; color: var(--t-primary);
  line-height: 1.35; margin-bottom: 6px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.card-meta {
  font-size: 12px; color: var(--t-faint); margin-bottom: 14px;
  display: flex; gap: 4px;
}

/* Card footer */
.card-footer {
  display: flex; justify-content: space-between; align-items: center;
  padding-top: 12px; border-top: 1px solid var(--border-light);
}
.card-rehearsal-count {
  display: flex; align-items: center; gap: 4px;
  font-size: 12px; color: var(--t-faint);
}
.card-actions { display: flex; gap: 6px; }
.card-btn {
  width: 30px; height: 30px; border-radius: var(--radius-sm);
  background: var(--bg-content); border: 1px solid var(--border);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: all 0.15s; color: var(--t-muted);
}
.card-btn:hover { background: var(--accent-light); border-color: var(--accent); color: var(--accent); }
.card-btn svg { width: 15px; height: 15px; }

/* Add card */
.add-card {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 8px; min-height: 180px;
  background: var(--bg-content); border: 1.5px dashed var(--border);
  box-shadow: none; color: var(--t-faint);
}
.add-card:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-dim); }
.add-icon { color: inherit; }
.add-label { font-size: 13.5px; font-weight: 600; color: inherit; }
.add-sub   { font-size: 12px; color: var(--t-faint); }

/* Empty state */
.empty-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 64px 24px; text-align: center;
}
.empty-icon  { margin-bottom: 12px; color: var(--t-faint); }
.empty-text  { font-size: 16px; font-weight: 600; color: var(--t-secondary); margin-bottom: 6px; }
.empty-sub   { font-size: 13px; color: var(--t-faint); }

/* ── Custom modal ────────────────────────────────── */
.modal-backdrop {
  position: fixed; inset: 0; z-index: 2000;
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(2px);
  display: flex; align-items: center; justify-content: center;
}

.modal-card {
  width: 520px;
  background: var(--bg-card);
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.18), 0 4px 16px rgba(0,0,0,0.08);
  display: flex; flex-direction: column;
  overflow: hidden;
}

/* Header */
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 20px 24px 18px;
  border-bottom: 1px solid var(--border-light);
}
.modal-header-left { display: flex; align-items: center; gap: 12px; }
.modal-icon {
  width: 36px; height: 36px; border-radius: 10px;
  background: var(--accent-dim);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  color: var(--accent);
}
.modal-icon svg { width: 18px; height: 18px; }
.modal-title { font-size: 16px; font-weight: 700; color: var(--t-primary); line-height: 1.2; }
.modal-subtitle { font-size: 12px; color: var(--t-faint); margin-top: 2px; }
.modal-close {
  width: 28px; height: 28px; border-radius: 7px; border: none;
  background: transparent; color: var(--t-faint);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: all 0.15s;
}
.modal-close:hover { background: var(--bg-content); color: var(--t-primary); }
.modal-close svg { width: 14px; height: 14px; }

/* Body */
.modal-body { padding: 20px 24px; }

.form-row {
  display: grid; grid-template-columns: 1fr 1fr; gap: 14px;
}

/* Override Element Plus form label */
.v2-form :deep(.el-form-item__label) {
  font-size: 12px; font-weight: 600;
  color: var(--t-secondary);
  letter-spacing: 0.1px;
  padding-bottom: 5px;
  line-height: 1.4;
}
.v2-form :deep(.el-form-item) {
  margin-bottom: 14px;
}
.v2-form :deep(.el-input__wrapper),
.v2-form :deep(.el-textarea__inner) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px var(--border);
  transition: box-shadow 0.15s;
}
.v2-form :deep(.el-input__wrapper:hover),
.v2-form :deep(.el-textarea__inner:hover) {
  box-shadow: 0 0 0 1px #9CA3AF;
}
.v2-form :deep(.el-input__wrapper.is-focus),
.v2-form :deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 2px var(--accent) !important;
}
.v2-form :deep(.el-select .el-input__wrapper) {
  border-radius: 8px;
}
.v2-form :deep(.el-input-number .el-input__wrapper) {
  border-radius: 8px;
}
.v2-form :deep(.el-date-editor .el-input__wrapper) {
  border-radius: 8px;
}
.v2-form :deep(.el-textarea__inner) {
  font-family: inherit;
  font-size: 13px;
  resize: none;
  padding: 8px 12px;
}
.v2-form :deep(.el-input__inner) {
  font-size: 13px;
}

.optional-tag {
  display: inline-block;
  margin-left: 6px; padding: 1px 6px;
  background: var(--bg-content);
  border-radius: 4px;
  font-size: 10px; font-weight: 600;
  color: var(--t-faint);
  letter-spacing: 0.2px;
  vertical-align: middle;
}

/* Footer */
.modal-footer {
  display: flex; align-items: center; justify-content: flex-end; gap: 10px;
  padding: 14px 24px 20px;
  border-top: 1px solid var(--border-light);
}
.modal-btn-cancel {
  height: 36px; padding: 0 18px;
  border-radius: 8px; border: 1px solid var(--border);
  background: var(--bg-card); color: var(--t-secondary);
  font-size: 13px; font-weight: 500; font-family: inherit;
  cursor: pointer; transition: all 0.15s;
}
.modal-btn-cancel:hover { background: var(--bg-content); border-color: #9CA3AF; }
.modal-btn-primary {
  height: 36px; padding: 0 20px;
  border-radius: 8px; border: none;
  background: var(--accent); color: #fff;
  font-size: 13px; font-weight: 600; font-family: inherit;
  cursor: pointer; transition: all 0.15s;
  display: flex; align-items: center; gap: 6px;
}
.modal-btn-primary:hover { background: #4F46E5; }
.modal-btn-primary:disabled { opacity: 0.7; cursor: not-allowed; }

/* Spinner */
.spin-icon { width: 14px; height: 14px; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Mobile ─────────────────────────────────────────── */
@media (max-width: 600px) {
  .v2-content { padding: 16px; }
  .page-header { padding: 16px; }
  .page-header h1 { font-size: 20px; }
  .new-task-btn span:last-child { display: none; }
  .project-grid { grid-template-columns: 1fr; }
  .filter-bar { overflow-x: auto; scrollbar-width: none; gap: 6px; flex-wrap: nowrap; }
  .filter-bar::-webkit-scrollbar { display: none; }
  .search-box { display: none; }
}

/* Modal transition */
.modal-enter-active, .modal-leave-active { transition: opacity 0.18s ease; }
.modal-enter-active .modal-card, .modal-leave-active .modal-card { transition: transform 0.18s ease, opacity 0.18s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .modal-card, .modal-leave-to .modal-card { transform: translateY(12px) scale(0.97); opacity: 0; }

/* Skeleton */
.skeleton {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.2s infinite;
  min-height: 180px; cursor: default;
}
@keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }

/* Import modal specific */
.import-card { max-width: 420px; }
.import-icon { background: rgba(16, 185, 129, 0.12); color: #10B981; }
.import-body {
  padding: 20px 24px 8px;
  display: flex; flex-direction: column; gap: 14px;
}
.import-step {
  display: flex; align-items: flex-start; gap: 12px;
  font-size: 14px; color: var(--t-primary); line-height: 1.5;
}
.step-num {
  width: 22px; height: 22px; border-radius: 50%;
  background: var(--accent); color: #fff;
  font-size: 11px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; margin-top: 1px;
}
</style>
