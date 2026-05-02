<template>
  <div>
    <!-- No plan yet: PPT upload panel -->
    <div v-if="!plan && !generating" class="upload-zone">
      <el-upload
        class="ppt-uploader"
        drag
        :auto-upload="false"
        :limit="1"
        accept=".pptx,.pdf"
        :on-change="handleFileChange"
      >
        <el-icon size="48" color="#409eff"><UploadFilled /></el-icon>
        <div class="upload-text">
          <p>拖拽 PPT 文件到此处，或<em>点击上传</em></p>
          <p class="upload-hint">支持 .pptx / .pdf，最大 50MB，最多 100 页</p>
        </div>
      </el-upload>

      <div v-if="selectedFile" class="upload-action">
        <el-tag type="info">{{ selectedFile.name }}</el-tag>
        <el-button type="primary" :loading="uploading" @click="handleGenerate">
          {{ uploading ? `上传中 ${uploadPct}%` : '上传并生成讲解方案' }}
        </el-button>
      </div>
    </div>

    <!-- Generating progress -->
    <div v-if="generating" class="generating-state">
      <el-progress type="circle" :percentage="genProgress" />
      <p class="gen-stage">{{ genStageText }}</p>
      <p class="gen-hint">AI 正在分析您的 PPT 并生成讲解方案，预计 30–60 秒…</p>
    </div>

    <!-- Plan view: left PPT thumbnails | right talking points -->
    <div v-if="plan && plan.status === 1 || plan?.status === 2" class="plan-layout">
      <div class="plan-header">
        <el-tag>第 {{ plan.version }} 版方案</el-tag>
        <el-tag v-if="plan.status === 2" type="warning">已人工修改</el-tag>
        <div class="plan-actions">
          <el-button size="small" :icon="Refresh" @click="handleRegenerate">重新生成</el-button>
          <el-button size="small" :icon="Upload" @click="handleReupload">上传新 PPT</el-button>
        </div>
      </div>

      <!-- Global strategy card -->
      <el-collapse class="strategy-card">
        <el-collapse-item name="strategy" title="全局述标策略">
          <div v-if="globalStrategy" class="strategy-content">
            <p><strong>开场策略：</strong>{{ globalStrategy.opening_approach }}</p>
            <p><strong>核心主线：</strong>{{ globalStrategy.core_narrative }}</p>
            <p><strong>收尾升华：</strong>{{ globalStrategy.closing_elevation }}</p>
            <p><strong>一句话要点：</strong>{{ globalStrategy.key_message }}</p>
            <p><strong>建议总时长：</strong>{{ Math.round((globalStrategy.total_duration_sec ?? 0) / 60) }} 分钟</p>
          </div>
        </el-collapse-item>
        <el-collapse-item v-if="plan.predicted_questions?.length" name="questions" title="评委问题预判">
          <div v-for="(q, i) in plan.predicted_questions" :key="i" class="question-item">
            <p class="q-text">Q{{ i+1 }}：{{ q.question }}</p>
            <p class="a-text">建议方向：{{ q.answer_direction }}</p>
          </div>
        </el-collapse-item>
      </el-collapse>

      <!-- Split layout -->
      <div class="split-layout">
        <!-- Left: slide thumbnails -->
        <div class="slide-list">
          <div
            v-for="page in plan.pages"
            :key="page.page_number"
            class="slide-item"
            :class="{ active: activePage === page.page_number }"
            @click="activePage = page.page_number"
          >
            <div class="slide-thumb-wrapper">
              <img
                v-if="page.page_thumbnail_url"
                :src="page.page_thumbnail_url"
                class="slide-thumb"
                :alt="`第${page.page_number}页`"
              />
              <div v-else class="slide-thumb-placeholder">{{ page.page_number }}</div>
            </div>
            <div class="slide-info">
              <span class="slide-num">{{ page.page_number }}</span>
              <el-tag size="small" :type="importanceTagType(page.importance_level)">
                {{ IMPORTANCE_LABELS[page.importance_level] }}
              </el-tag>
            </div>
          </div>
        </div>

        <!-- Right: talking points for selected page -->
        <div class="page-detail" v-if="activePage && selectedPageData">
          <div class="page-detail-header">
            <h3>第 {{ activePage }} 页：{{ selectedPageData.page_title || '(无标题)' }}</h3>
            <div class="page-meta">
              <el-tag :type="importanceTagType(selectedPageData.importance_level)">
                {{ IMPORTANCE_LABELS[selectedPageData.importance_level] }}
              </el-tag>
              <span class="duration-badge">
                <el-icon><Timer /></el-icon>
                建议 {{ selectedPageData.suggested_duration }}秒
              </span>
              <el-tag v-if="selectedPageData.is_manually_edited" type="warning" size="small">已人工修改</el-tag>
            </div>
          </div>

          <!-- Editable talking points -->
          <div class="section-title">讲解要点</div>
          <div v-if="!editingPage" class="talking-points">
            <div
              v-for="(tp, i) in selectedPageData.talking_points"
              :key="i"
              class="tp-item"
              :class="{ emphasis: tp.is_emphasis }"
            >
              <el-icon v-if="tp.is_emphasis" color="#e6a23c"><Star /></el-icon>
              <el-icon v-else color="#909399"><ArrowRight /></el-icon>
              <span>{{ tp.point }}</span>
            </div>
            <el-button size="small" type="text" @click="startEdit">编辑</el-button>
          </div>

          <div v-else class="tp-editor">
            <div v-for="(tp, i) in editForm" :key="i" class="tp-edit-row">
              <el-checkbox v-model="tp.is_emphasis" label="重点" size="small" />
              <el-input v-model="tp.point" size="small" style="flex:1" />
              <el-button size="small" type="danger" :icon="Delete" circle @click="editForm.splice(i,1)" />
            </div>
            <el-button size="small" @click="editForm.push({ point: '', is_emphasis: false })">+ 添加要点</el-button>
            <div class="tp-edit-actions">
              <el-button @click="editingPage = false">取消</el-button>
              <el-button type="primary" :loading="saving" @click="savePage">保存</el-button>
            </div>
          </div>

          <!-- Emphasis marks -->
          <template v-if="selectedPageData.emphasis_marks?.length">
            <div class="section-title">重音标记</div>
            <div class="emphasis-chips">
              <el-tag v-for="em in selectedPageData.emphasis_marks" :key="em.text" type="warning" size="small">
                《{{ em.text }}》
              </el-tag>
            </div>
          </template>

          <!-- Transition hint -->
          <template v-if="selectedPageData.transition_hint">
            <div class="section-title">过渡话术</div>
            <p class="transition-text">{{ selectedPageData.transition_hint }}</p>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Refresh, Upload, Delete, ArrowRight, Star, Timer, UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { pitchPlanApi, type PitchPlan, type TalkingPoint } from '@/api/pitchPlan'
import { useWebSocket } from '@/composables/useWebSocket'
import type { PitchTask } from '@/api/pitchTask'

const props = defineProps<{ task: PitchTask; plan: PitchPlan | null }>()
const emit = defineEmits<{ 'plan-created': [plan: PitchPlan] }>()

const IMPORTANCE_LABELS: Record<number, string> = { 1: '快速带过', 2: '重要', 3: '核心' }

const selectedFile = ref<File | null>(null)
const uploading = ref(false)
const uploadPct = ref(0)
const generating = ref(false)
const genProgress = ref(0)
const genStageText = ref('正在准备…')
const activePage = ref(1)
const editingPage = ref(false)
const editForm = ref<TalkingPoint[]>([])
const saving = ref(false)
const currentPlanId = ref<number | null>(props.plan?.id ?? null)
const localPlan = ref<PitchPlan | null>(props.plan)

watch(() => props.plan, (p) => { localPlan.value = p; if (p) currentPlanId.value = p.id })

// Re-expose plan computed
const plan = computed(() => localPlan.value)
const selectedPageData = computed(() => plan.value?.pages.find(p => p.page_number === activePage.value))
const globalStrategy = computed(() => {
  if (!plan.value?.global_strategy) return null
  try { return JSON.parse(plan.value.global_strategy) } catch { return null }
})

// WebSocket for progress updates
useWebSocket((evt) => {
  if (evt.entity_type === 'plan' && evt.entity_id === currentPlanId.value) {
    genProgress.value = evt.progress
    genStageText.value = stageLabel(evt.stage)
    if (evt.progress >= 100) {
      generating.value = false
      loadPlan(currentPlanId.value!)
    }
  }
})

function stageLabel(stage: string): string {
  const map: Record<string, string> = {
    downloading_ppt: '正在下载 PPT…',
    parsing_ppt: '解析幻灯片内容…',
    generating_plan: '调用 AI 生成讲解方案…',
    sending_to_llm: '分析 PPT 结构…',
    parsing_response: '整理方案内容…',
    saving_results: '保存方案…',
    done: '完成！',
  }
  return map[stage] ?? stage
}

async function loadPlan(planId: number) {
  const res = await pitchPlanApi.get(planId)
  localPlan.value = res.data
  emit('plan-created', res.data)
}

function handleFileChange(file: any) {
  selectedFile.value = file.raw as File
}

async function handleGenerate() {
  if (!selectedFile.value) return
  uploading.value = true
  uploadPct.value = 0
  try {
    const urlRes = await pitchPlanApi.getUploadUrl(selectedFile.value.name)
    const { upload_url, object_key } = urlRes.data
    await pitchPlanApi.uploadToMinio(upload_url, selectedFile.value, (pct) => { uploadPct.value = pct })

    uploading.value = false
    generating.value = true
    genProgress.value = 0

    const genRes = await pitchPlanApi.generate({
      pitch_task_id: props.task.id,
      ppt_file_id: object_key,
      ppt_file_name: selectedFile.value.name,
      bid_requirements: props.task.bid_date ? undefined : undefined,
      bid_time_limit: props.task.bid_time_limit ?? 30,
    })
    currentPlanId.value = genRes.data.plan_id
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '操作失败')
    uploading.value = false
    generating.value = false
  }
}

async function handleRegenerate() {
  if (!plan.value) return
  generating.value = true
  genProgress.value = 0
  await pitchPlanApi.regenerate(plan.value.id)
}

function handleReupload() {
  localPlan.value = null
  selectedFile.value = null
}

function startEdit() {
  if (!selectedPageData.value) return
  editForm.value = selectedPageData.value.talking_points.map(tp => ({ ...tp }))
  editingPage.value = true
}

async function savePage() {
  if (!plan.value || !selectedPageData.value) return
  saving.value = true
  try {
    const updated = await pitchPlanApi.updatePage(plan.value.id, activePage.value, {
      talking_points: editForm.value,
    })
    const idx = localPlan.value!.pages.findIndex(p => p.page_number === activePage.value)
    if (idx !== -1) localPlan.value!.pages[idx] = updated.data
    editingPage.value = false
    ElMessage.success('已保存')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

function importanceTagType(level: number) {
  return level === 3 ? 'danger' : level === 2 ? 'warning' : 'info'
}
</script>

<style scoped>
.upload-zone { padding: 32px; text-align: center; }
.ppt-uploader :deep(.el-upload-dragger) { width: 480px; height: 180px; display: flex; align-items: center; justify-content: center; flex-direction: column; gap: 12px; }
.upload-text p { color: #606266; } .upload-text em { color: #409eff; font-style: normal; }
.upload-hint { font-size: 12px; color: #909399 !important; }
.upload-action { margin-top: 16px; display: flex; align-items: center; gap: 12px; justify-content: center; }

.generating-state { text-align: center; padding: 60px; }
.gen-stage { margin-top: 16px; font-size: 15px; color: #409eff; font-weight: 500; }
.gen-hint { color: #909399; font-size: 13px; margin-top: 8px; }

.plan-header { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
.plan-actions { margin-left: auto; display: flex; gap: 8px; }

.strategy-card { margin-bottom: 16px; }
.strategy-content p { margin-bottom: 8px; font-size: 14px; color: #606266; }
.question-item { padding: 8px 0; border-bottom: 1px solid #f0f0f0; }
.q-text { font-weight: 500; color: #303133; }
.a-text { color: #606266; font-size: 13px; margin-top: 4px; }

.split-layout { display: flex; gap: 0; border: 1px solid #e4e7ed; border-radius: 8px; overflow: hidden; }

.slide-list { width: 180px; border-right: 1px solid #e4e7ed; background: #fafafa; overflow-y: auto; max-height: 680px; }
.slide-item { padding: 8px; cursor: pointer; border-bottom: 1px solid #f0f0f0; transition: background 0.15s; }
.slide-item.active { background: #ecf5ff; }
.slide-item:hover:not(.active) { background: #f5f7fa; }
.slide-thumb-wrapper { width: 100%; aspect-ratio: 4/3; background: #e4e7ed; border-radius: 4px; overflow: hidden; }
.slide-thumb { width: 100%; height: 100%; object-fit: cover; }
.slide-thumb-placeholder { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; color: #909399; font-size: 20px; font-weight: 700; }
.slide-info { display: flex; align-items: center; justify-content: space-between; margin-top: 4px; }
.slide-num { font-size: 12px; color: #909399; }

.page-detail { flex: 1; padding: 20px; overflow-y: auto; max-height: 680px; }
.page-detail-header { margin-bottom: 16px; }
.page-detail-header h3 { font-size: 16px; font-weight: 600; color: #303133; margin-bottom: 8px; }
.page-meta { display: flex; align-items: center; gap: 8px; }
.duration-badge { display: flex; align-items: center; gap: 4px; font-size: 13px; color: #606266; }

.section-title { font-size: 13px; font-weight: 600; color: #909399; margin: 16px 0 8px; text-transform: uppercase; letter-spacing: 0.5px; }

.talking-points { display: flex; flex-direction: column; gap: 8px; }
.tp-item { display: flex; align-items: flex-start; gap: 8px; font-size: 14px; color: #303133; }
.tp-item.emphasis { color: #b7872a; font-weight: 500; }

.tp-editor { display: flex; flex-direction: column; gap: 8px; }
.tp-edit-row { display: flex; align-items: center; gap: 8px; }
.tp-edit-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px; }

.emphasis-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.transition-text { font-size: 13px; color: #606266; font-style: italic; background: #f5f7fa; padding: 8px 12px; border-radius: 6px; border-left: 3px solid #409eff; }
</style>
