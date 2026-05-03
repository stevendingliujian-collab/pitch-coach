<template>
  <div class="rubric-tab">
    <!-- Empty state: no rubrics and no selected rehearsal -->
    <div v-if="!rubrics.length && !loading" class="rubric-empty-state">
      <div class="empty-icon">
        <svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="6" y="4" width="36" height="40" rx="3"/>
          <line x1="14" y1="14" x2="34" y2="14"/>
          <line x1="14" y1="21" x2="34" y2="21"/>
          <line x1="14" y1="28" x2="24" y2="28"/>
          <polyline points="29 33 33 37 40 29"/>
        </svg>
      </div>
      <h3 class="empty-title">还没有评分表</h3>
      <p class="empty-desc">导入预设模板或手动创建评分表，在排练完成后对标评委打分标准</p>
      <div class="empty-actions">
        <button class="btn-primary" @click="showTemplates = true">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="1" width="10" height="12" rx="1"/><line x1="5" y1="7" x2="9" y2="7"/>
            <line x1="7" y1="5" x2="7" y2="9"/>
          </svg>
          导入预设模板
        </button>
        <button class="btn-outline" @click="openCreateDialog">手动创建</button>
      </div>
    </div>

    <!-- Main content -->
    <div v-else class="rubric-layout">
      <!-- Left: rubric list -->
      <div class="rubric-list-panel">
        <div class="panel-header">
          <span class="panel-title">评分表</span>
          <div class="panel-actions">
            <button class="icon-btn" title="导入模板" @click="showTemplates = true">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M7 1v8M3.5 6l3.5 4 3.5-4"/><rect x="1" y="11" width="12" height="2" rx="1"/>
              </svg>
            </button>
            <button class="icon-btn" title="新建评分表" @click="openCreateDialog">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="7" y1="2" x2="7" y2="12"/><line x1="2" y1="7" x2="12" y2="7"/>
              </svg>
            </button>
          </div>
        </div>

        <div v-if="loading" class="list-loading">
          <el-skeleton :rows="3" animated />
        </div>
        <div v-else class="rubric-items">
          <div
            v-for="rubric in rubrics"
            :key="rubric.id"
            class="rubric-list-item"
            :class="{ active: selectedRubricId === rubric.id }"
            @click="selectRubric(rubric.id)"
          >
            <div class="ri-name">{{ rubric.name }}</div>
            <div class="ri-meta">
              <span class="ri-industry">{{ rubric.industry || '通用' }}</span>
              <span class="ri-count">{{ rubric.items.length }} 项</span>
              <span class="ri-score">满分 {{ rubric.total_max_score }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Right: rubric detail + scoring -->
      <div class="rubric-detail-panel" v-if="selectedRubric">
        <!-- Rubric header -->
        <div class="detail-header">
          <div class="detail-title-row">
            <h2 class="detail-title">{{ selectedRubric.name }}</h2>
            <div class="detail-meta">
              <span class="meta-tag">{{ selectedRubric.industry || '通用' }}</span>
              <span class="meta-tag">满分 {{ selectedRubric.total_max_score }} 分</span>
            </div>
          </div>
          <p v-if="selectedRubric.description" class="detail-desc">{{ selectedRubric.description }}</p>

          <!-- Score against rehearsal -->
          <div class="score-action-bar">
            <select class="rehearsal-select" v-model="selectedRehearsalId">
              <option :value="null" disabled>选择排练记录进行对标…</option>
              <option v-for="r in rehearsals" :key="r.id" :value="r.id">
                {{ formatDate(r.created_at) }} · {{ r.total_score ? Math.round(Number(r.total_score)) + '分' : '未评分' }}
              </option>
            </select>
            <button
              class="btn-primary"
              :disabled="!selectedRehearsalId || scoring"
              @click="triggerScore"
            >
              <svg v-if="scoring" class="spin" width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M7 1.5a5.5 5.5 0 110 11 5.5 5.5 0 010-11" stroke-dasharray="20" stroke-dashoffset="10"/>
              </svg>
              {{ scoring ? 'AI评分中…' : '开始评分对标' }}
            </button>
          </div>
        </div>

        <!-- Items table (without score) -->
        <div v-if="!rubricScore" class="items-table">
          <div class="items-table-header">
            <span class="col-cat">分类</span>
            <span class="col-item">评分项</span>
            <span class="col-max">满分</span>
            <span class="col-desc">说明</span>
          </div>
          <div
            v-for="item in selectedRubric.items"
            :key="item.id"
            class="items-table-row"
          >
            <span class="col-cat">
              <span class="cat-badge">{{ item.category }}</span>
            </span>
            <span class="col-item item-name">{{ item.item }}</span>
            <span class="col-max">{{ item.max_score }}</span>
            <span class="col-desc item-desc">{{ item.description }}</span>
          </div>
        </div>

        <!-- Coverage result -->
        <div v-else class="coverage-result">
          <!-- Summary row -->
          <div class="coverage-summary">
            <div class="summary-card">
              <div class="sum-num" :class="scoreClass">{{ Math.round(rubricScore.total_score || 0) }}</div>
              <div class="sum-label">总得分</div>
              <div class="sum-max">/ {{ selectedRubric.total_max_score }}</div>
            </div>
            <div class="summary-card">
              <div class="sum-num green">{{ Math.round((rubricScore.coverage_percent || 0) * 100) }}%</div>
              <div class="sum-label">覆盖率</div>
            </div>
            <div class="summary-card">
              <div class="sum-num">{{ coveredCount }}</div>
              <div class="sum-label">已覆盖项</div>
              <div class="sum-max">/ {{ selectedRubric.items.length }}</div>
            </div>
            <button class="btn-outline btn-sm" @click="rubricScore = null">重新对标</button>
          </div>

          <!-- Per-item results -->
          <div class="score-items">
            <div
              v-for="item in selectedRubric.items"
              :key="item.id"
              class="score-item"
              :class="{ covered: getScoreItem(item.id)?.coverage, uncovered: !getScoreItem(item.id)?.coverage }"
            >
              <div class="score-item-header">
                <span class="cat-badge">{{ item.category }}</span>
                <span class="si-name">{{ item.item }}</span>
                <div class="si-score-bar">
                  <div
                    class="si-score-fill"
                    :style="{
                      width: (getScoreItem(item.id)?.score || 0) / item.max_score * 100 + '%',
                      background: getScoreItem(item.id)?.coverage ? '#22C55E' : '#EF4444'
                    }"
                  />
                </div>
                <span class="si-score">
                  {{ getScoreItem(item.id)?.score || 0 }}/{{ item.max_score }}
                </span>
                <span class="coverage-dot" :class="{ covered: getScoreItem(item.id)?.coverage }">
                  {{ getScoreItem(item.id)?.coverage ? '✓' : '✗' }}
                </span>
              </div>
              <div v-if="getScoreItem(item.id)?.note" class="si-note">{{ getScoreItem(item.id)?.note }}</div>
              <div v-if="getSuggestion(item.id)" class="si-suggestion">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.8">
                  <circle cx="6" cy="6" r="5"/><line x1="6" y1="5" x2="6" y2="8"/><circle cx="6" cy="3.5" r="0.5" fill="currentColor"/>
                </svg>
                {{ getSuggestion(item.id) }}
              </div>
            </div>
          </div>

          <!-- Heat map -->
          <div class="coverage-heatmap">
            <div class="heatmap-title">覆盖度热力图</div>
            <div class="heatmap-grid">
              <div
                v-for="item in selectedRubric.items"
                :key="item.id"
                class="heatmap-cell"
                :class="heatmapClass(item)"
                :title="`${item.item}: ${getScoreItem(item.id)?.score || 0}/${item.max_score}`"
              >
                <span class="hc-label">{{ item.item.slice(0, 6) }}</span>
              </div>
            </div>
            <div class="heatmap-legend">
              <span class="legend-dot green">● 高覆盖</span>
              <span class="legend-dot yellow">● 中覆盖</span>
              <span class="legend-dot red">● 未覆盖</span>
            </div>
          </div>
        </div>
      </div>

      <!-- No rubric selected -->
      <div v-else class="rubric-no-select">
        <span>← 选择左侧评分表查看详情</span>
      </div>
    </div>

    <!-- Template picker dialog -->
    <Teleport to="body">
      <Transition name="modal-fade">
        <div v-if="showTemplates" class="modal-backdrop" @click.self="showTemplates = false">
          <div class="modal-box">
            <div class="modal-header">
              <h3>选择预设模板</h3>
              <button class="modal-close" @click="showTemplates = false">✕</button>
            </div>
            <div class="template-grid">
              <div
                v-for="tmpl in presetTemplates"
                :key="tmpl.template_type"
                class="template-card"
                @click="importTemplate(tmpl.template_type)"
              >
                <div class="tmpl-name">{{ tmpl.name }}</div>
                <div class="tmpl-industry">{{ tmpl.industry }}</div>
                <div class="tmpl-desc">{{ tmpl.description }}</div>
                <div class="tmpl-items-count">{{ tmpl.items.length }} 个评分项 · 满分 {{ tmpl.total_max_score }}</div>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { rubricsApi, type ScoringRubric, type RubricScore, type PresetTemplate } from '@/api/rubrics'

const props = defineProps<{
  taskId: number
  planId: number | null
}>()

const loading = ref(false)
const rubrics = ref<ScoringRubric[]>([])
const selectedRubricId = ref<number | null>(null)
const selectedRehearsalId = ref<number | null>(null)
const rubricScore = ref<RubricScore | null>(null)
const scoring = ref(false)
const showTemplates = ref(false)
const presetTemplates = ref<PresetTemplate[]>([])

// Stub rehearsal list — in a real integration, fetch from rehearsal API
const rehearsals = ref<Array<{ id: number; created_at: string; total_score: string | null }>>([])

const selectedRubric = computed(() =>
  rubrics.value.find(r => r.id === selectedRubricId.value) ?? null
)

const coveredCount = computed(() => {
  if (!rubricScore.value) return 0
  return rubricScore.value.scores.filter(s => s.coverage).length
})

const scoreClass = computed(() => {
  const s = rubricScore.value?.total_score || 0
  const max = selectedRubric.value?.total_max_score || 100
  const pct = s / max
  if (pct >= 0.8) return 'green'
  if (pct >= 0.6) return 'orange'
  return 'red'
})

onMounted(async () => {
  await loadRubrics()
  await loadTemplates()
  await loadRehearsals()
})

async function loadRubrics() {
  loading.value = true
  try {
    const res = await rubricsApi.list()
    rubrics.value = res.data
    if (rubrics.value.length && !selectedRubricId.value) {
      selectedRubricId.value = rubrics.value[0].id
    }
  } finally {
    loading.value = false
  }
}

async function loadTemplates() {
  try {
    const res = await rubricsApi.listTemplates()
    presetTemplates.value = res.data
  } catch {}
}

async function loadRehearsals() {
  // Import rehearsal API dynamically to avoid circular deps
  try {
    const { rehearsalApi } = await import('@/api/rehearsal')
    const res = await rehearsalApi.listByTask(props.taskId)
    rehearsals.value = res.data
      .filter((r: any) => r.status >= 3)
      .map((r: any) => ({ id: r.id, created_at: r.created_at, total_score: r.total_score }))
  } catch {}
}

function selectRubric(id: number) {
  selectedRubricId.value = id
  rubricScore.value = null
}

async function importTemplate(templateType: string) {
  try {
    const res = await rubricsApi.importTemplate(templateType)
    rubrics.value.push(res.data)
    selectedRubricId.value = res.data.id
    showTemplates.value = false
    ElMessage.success('模板已导入')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '导入失败')
  }
}

function openCreateDialog() {
  ElMessage.info('手动创建评分表功能即将上线，当前可先使用预设模板')
}

async function triggerScore() {
  if (!selectedRubricId.value || !selectedRehearsalId.value) return
  scoring.value = true
  try {
    const res = await rubricsApi.scoreCoverage(selectedRubricId.value, selectedRehearsalId.value)
    rubricScore.value = res.data
    ElMessage.success('评分对标完成！')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || 'AI评分失败')
  } finally {
    scoring.value = false
  }
}

function getScoreItem(itemId: string) {
  return rubricScore.value?.scores.find(s => String(s.item_id) === String(itemId)) ?? null
}

function getSuggestion(itemId: string) {
  return rubricScore.value?.improvement_suggestions?.find(s => String(s.item_id) === String(itemId))?.suggestion ?? null
}

function heatmapClass(item: any) {
  const si = getScoreItem(item.id)
  if (!si) return 'hc-gray'
  const pct = si.score / item.max_score
  if (pct >= 0.75) return 'hc-green'
  if (pct >= 0.4) return 'hc-yellow'
  return 'hc-red'
}

function formatDate(iso: string) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>

<style scoped>
.rubric-tab {
  height: calc(100vh - 120px);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* ── Empty state ─────────────────────────────── */
.rubric-empty-state {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 16px;
  padding: 80px 24px; text-align: center;
}
.empty-icon svg {
  width: 64px; height: 64px;
  color: var(--t-faint, #BBBDC4);
}
.empty-title { font-size: 18px; font-weight: 700; color: var(--t-primary, #0F0F13); margin: 0; }
.empty-desc { font-size: 13px; color: var(--t-muted, #8B8D99); max-width: 360px; line-height: 1.6; margin: 0; }
.empty-actions { display: flex; gap: 10px; }

/* ── Layout ──────────────────────────────────── */
.rubric-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
  gap: 0;
}

/* ── Left panel ──────────────────────────────── */
.rubric-list-panel {
  width: 240px;
  flex-shrink: 0;
  border-right: 1px solid var(--border, rgba(0,0,0,0.07));
  display: flex; flex-direction: column;
  overflow: hidden;
}
.panel-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px 10px;
  border-bottom: 1px solid var(--border, rgba(0,0,0,0.07));
  flex-shrink: 0;
}
.panel-title { font-size: 13px; font-weight: 700; color: var(--t-primary, #0F0F13); }
.panel-actions { display: flex; gap: 4px; }
.icon-btn {
  width: 26px; height: 26px; border-radius: 6px; border: none;
  background: transparent; color: var(--t-muted, #8B8D99);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: all 0.15s;
}
.icon-btn:hover { background: var(--bg-content, #F5F5F7); color: var(--t-primary, #0F0F13); }

.rubric-items { flex: 1; overflow-y: auto; padding: 8px; }
.rubric-list-item {
  padding: 10px 10px; border-radius: 8px;
  cursor: pointer; transition: background 0.15s;
  margin-bottom: 2px;
}
.rubric-list-item:hover { background: var(--bg-content, #F5F5F7); }
.rubric-list-item.active { background: rgba(99,102,241,0.08); }
.ri-name { font-size: 13px; font-weight: 600; color: var(--t-primary, #0F0F13); margin-bottom: 4px; }
.ri-meta { display: flex; gap: 6px; flex-wrap: wrap; }
.ri-industry, .ri-count, .ri-score {
  font-size: 11px; color: var(--t-muted, #8B8D99);
}
.ri-industry { color: #6366F1; font-weight: 600; }

/* ── Right panel ─────────────────────────────── */
.rubric-detail-panel {
  flex: 1; overflow-y: auto;
  display: flex; flex-direction: column;
}
.rubric-no-select {
  flex: 1; display: flex; align-items: center; justify-content: center;
  font-size: 13px; color: var(--t-faint, #BBBDC4);
}
.detail-header {
  padding: 20px 24px 16px;
  border-bottom: 1px solid var(--border, rgba(0,0,0,0.07));
  flex-shrink: 0;
}
.detail-title-row {
  display: flex; align-items: center; gap: 12px; margin-bottom: 6px;
}
.detail-title { font-size: 17px; font-weight: 800; color: var(--t-primary, #0F0F13); margin: 0; }
.detail-meta { display: flex; gap: 6px; }
.meta-tag {
  font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 20px;
  background: rgba(99,102,241,0.08); color: #6366F1;
}
.detail-desc { font-size: 12.5px; color: var(--t-muted, #8B8D99); margin: 4px 0 14px; }

.score-action-bar {
  display: flex; gap: 10px; align-items: center;
}
.rehearsal-select {
  flex: 1; max-width: 280px;
  height: 34px; border-radius: 8px;
  border: 1px solid var(--border, rgba(0,0,0,0.12));
  background: #fff; font-size: 12.5px;
  padding: 0 10px; color: var(--t-primary, #0F0F13);
  cursor: pointer;
}

/* ── Items table ─────────────────────────────── */
.items-table { padding: 16px 24px; }
.items-table-header {
  display: grid;
  grid-template-columns: 100px 1fr 60px 1fr;
  gap: 8px;
  padding: 8px 12px; border-radius: 8px;
  background: var(--bg-content, #F5F5F7);
  font-size: 11.5px; font-weight: 700; color: var(--t-muted, #8B8D99);
  text-transform: uppercase; letter-spacing: 0.5px;
  margin-bottom: 4px;
}
.items-table-row {
  display: grid;
  grid-template-columns: 100px 1fr 60px 1fr;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border, rgba(0,0,0,0.05));
  align-items: start;
  font-size: 13px;
}
.cat-badge {
  display: inline-block;
  padding: 2px 7px; border-radius: 20px;
  background: rgba(99,102,241,0.08); color: #6366F1;
  font-size: 11px; font-weight: 600; white-space: nowrap;
}
.item-name { font-weight: 600; color: var(--t-primary, #0F0F13); }
.item-desc { font-size: 12px; color: var(--t-muted, #8B8D99); line-height: 1.5; }
.col-max { text-align: center; font-weight: 700; color: var(--t-primary, #0F0F13); }

/* ── Coverage result ─────────────────────────── */
.coverage-result { padding: 16px 24px; }
.coverage-summary {
  display: flex; align-items: center; gap: 16px;
  padding: 16px 20px; border-radius: 12px;
  background: var(--bg-content, #F5F5F7);
  margin-bottom: 20px;
}
.summary-card { text-align: center; }
.sum-num { font-size: 28px; font-weight: 800; color: var(--t-primary, #0F0F13); }
.sum-num.green { color: #22C55E; }
.sum-num.orange { color: #F97316; }
.sum-num.red { color: #EF4444; }
.sum-label { font-size: 11px; color: var(--t-muted, #8B8D99); }
.sum-max { font-size: 11px; color: var(--t-faint, #BBBDC4); }

.score-items { display: flex; flex-direction: column; gap: 8px; margin-bottom: 20px; }
.score-item {
  border-radius: 10px; padding: 12px 14px;
  border: 1px solid var(--border, rgba(0,0,0,0.07));
  background: #fff;
}
.score-item.uncovered { border-color: rgba(239,68,68,0.2); background: rgba(239,68,68,0.02); }
.score-item-header {
  display: flex; align-items: center; gap: 8px;
}
.si-name { flex: 1; font-size: 13px; font-weight: 600; color: var(--t-primary, #0F0F13); }
.si-score-bar {
  width: 80px; height: 4px; border-radius: 2px;
  background: rgba(0,0,0,0.07); overflow: hidden; flex-shrink: 0;
}
.si-score-fill { height: 100%; border-radius: 2px; transition: width 0.4s; }
.si-score { font-size: 12px; font-weight: 700; color: var(--t-primary, #0F0F13); flex-shrink: 0; }
.coverage-dot {
  width: 18px; height: 18px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 10px; font-weight: 700; flex-shrink: 0;
  background: rgba(239,68,68,0.1); color: #EF4444;
}
.coverage-dot.covered { background: rgba(34,197,94,0.1); color: #22C55E; }
.si-note {
  font-size: 12px; color: var(--t-muted, #8B8D99);
  margin-top: 6px; padding-left: 4px; line-height: 1.5;
}
.si-suggestion {
  display: flex; align-items: flex-start; gap: 5px;
  font-size: 12px; color: #6366F1;
  margin-top: 6px; padding-left: 4px; line-height: 1.5;
}
.si-suggestion svg { flex-shrink: 0; margin-top: 1px; }

/* ── Heatmap ─────────────────────────────────── */
.coverage-heatmap {
  background: var(--bg-content, #F5F5F7);
  border-radius: 12px; padding: 16px 18px;
}
.heatmap-title { font-size: 12.5px; font-weight: 700; color: var(--t-muted, #8B8D99); margin-bottom: 12px; }
.heatmap-grid { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
.heatmap-cell {
  padding: 6px 10px; border-radius: 7px;
  font-size: 11px; font-weight: 600;
  cursor: default;
}
.hc-green { background: rgba(34,197,94,0.15); color: #15803D; }
.hc-yellow { background: rgba(249,115,22,0.12); color: #B45309; }
.hc-red { background: rgba(239,68,68,0.1); color: #DC2626; }
.hc-gray { background: rgba(0,0,0,0.06); color: #9CA3AF; }
.hc-label { white-space: nowrap; }
.heatmap-legend { display: flex; gap: 14px; }
.legend-dot { font-size: 11.5px; color: var(--t-muted, #8B8D99); }
.legend-dot.green { color: #22C55E; }
.legend-dot.yellow { color: #F97316; }
.legend-dot.red { color: #EF4444; }

/* ── Buttons ─────────────────────────────────── */
.btn-primary {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 8px 16px; border-radius: 8px;
  background: #6366F1; color: #fff;
  font-size: 13px; font-weight: 600; border: none; cursor: pointer;
  transition: background 0.15s;
}
.btn-primary:hover:not(:disabled) { background: #4F46E5; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-outline {
  padding: 8px 16px; border-radius: 8px;
  border: 1.5px solid var(--border, rgba(0,0,0,0.12));
  background: transparent; color: var(--t-primary, #0F0F13);
  font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.15s;
}
.btn-outline:hover { background: var(--bg-content, #F5F5F7); }
.btn-sm { padding: 5px 12px; font-size: 12px; }

/* ── Spin ────────────────────────────────────── */
.spin { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Modal ───────────────────────────────────── */
.modal-backdrop {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0,0,0,0.4); backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center; padding: 24px;
}
.modal-box {
  background: #fff; border-radius: 16px;
  width: 640px; max-width: 100%; max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 24px 80px rgba(0,0,0,0.18);
}
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 20px 24px 16px;
  border-bottom: 1px solid rgba(0,0,0,0.07);
  position: sticky; top: 0; background: #fff; z-index: 1;
}
.modal-header h3 { font-size: 16px; font-weight: 800; margin: 0; }
.modal-close {
  width: 28px; height: 28px; border-radius: 8px; border: none;
  background: rgba(0,0,0,0.05); cursor: pointer; font-size: 12px;
  display: flex; align-items: center; justify-content: center;
}
.modal-close:hover { background: rgba(0,0,0,0.1); }

.template-grid { padding: 16px 24px 24px; display: flex; flex-direction: column; gap: 10px; }
.template-card {
  border: 1.5px solid rgba(0,0,0,0.07); border-radius: 12px;
  padding: 16px 18px; cursor: pointer; transition: all 0.15s;
}
.template-card:hover { border-color: #6366F1; box-shadow: 0 0 0 3px rgba(99,102,241,0.1); }
.tmpl-name { font-size: 14px; font-weight: 700; color: #0F0F13; margin-bottom: 2px; }
.tmpl-industry { font-size: 11px; font-weight: 700; color: #6366F1; margin-bottom: 6px; }
.tmpl-desc { font-size: 12.5px; color: #8B8D99; line-height: 1.5; margin-bottom: 6px; }
.tmpl-items-count { font-size: 11.5px; color: #BBBDC4; font-weight: 600; }

.modal-fade-enter-active, .modal-fade-leave-active { transition: opacity 0.2s; }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; }

/* ── Loading ─────────────────────────────────── */
.list-loading { padding: 12px; }
</style>
