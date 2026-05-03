<template>
  <div class="narration-tab">
    <!-- No plan yet -->
    <el-empty v-if="!plan || plan.status < 1" description="请先生成讲解方案" />

    <!-- Generation controls -->
    <div v-else class="narration-header">
      <div class="narration-controls">
        <span class="label">音色：</span>
        <el-select v-model="selectedVoiceId" style="width: 140px" size="small" :loading="loadingVoices">
          <el-option v-for="v in voices" :key="v.id" :label="v.name" :value="v.id" />
        </el-select>

        <span class="label">语速：</span>
        <el-slider v-model="speed" :min="0.75" :max="1.5" :step="0.25"
          style="width: 140px" size="small" />
        <span class="speed-val">{{ speed }}x</span>

        <el-button type="primary" size="small" :loading="isActivelyGenerating" :disabled="isActivelyGenerating"
          @click="handleGenerate">
          {{ narration ? '重新生成示范' : '生成 AI 示范讲解' }}
        </el-button>

        <el-tag v-if="narration" :type="statusTagType" size="small" style="margin-left: 8px">
          {{ statusLabel }}
        </el-tag>
      </div>

      <!-- Progress bar while generating -->
      <el-progress v-if="generating" :percentage="genPct" :status="genPct < 100 ? '' : 'success'"
        style="margin-top: 12px" />
    </div>

    <!-- Main layout: PPT thumbnails | audio player + scripts -->
    <div v-if="narration && narration.status === 4" class="narration-layout">
      <!-- Left: PPT thumbnail strip -->
      <div class="thumb-strip">
        <div v-for="p in pages" :key="p.page_number"
          class="thumb-item" :class="{ active: currentPage === p.page_number }"
          @click="jumpToPage(p.page_number)">
          <el-image v-if="p.page_thumbnail_url" :src="p.page_thumbnail_url"
            fit="contain" class="thumb-img" />
          <div v-else class="thumb-placeholder">{{ p.page_number }}</div>
          <div class="thumb-num">{{ p.page_number }}</div>
          <el-tag v-if="pageAudio(p.page_number)" size="small" class="thumb-dur">
            {{ formatSec(pageAudio(p.page_number)!.duration_sec) }}
          </el-tag>
        </div>
      </div>

      <!-- Right: Script + player -->
      <div class="narration-main">
        <!-- Full audio player -->
        <div class="full-player">
          <div class="player-title">
            <el-icon><Headphones /></el-icon>
            完整讲解音频（{{ formatSec(narration.total_duration_sec ?? 0) }}）
          </div>
          <audio ref="fullAudioEl" :src="narration.total_audio_url ?? ''"
            controls preload="metadata" class="audio-ctrl"
            @timeupdate="onTimeUpdate" @ended="onEnded" />
          <div class="player-actions">
            <el-button size="small" @click="playAll">
              <el-icon><VideoPlay /></el-icon> 从头播放
            </el-button>
            <el-button size="small" :disabled="!canPlayPage" @click="playCurrentPage">
              <el-icon><VideoPlay /></el-icon> 播放当前页
            </el-button>
          </div>
        </div>

        <!-- Current page script -->
        <div v-if="currentPageAudio" class="script-panel">
          <div class="script-header">
            <span class="page-label">第 {{ currentPage }} 页</span>
            <el-tag size="small">{{ currentPageAudio.tone }}</el-tag>
            <el-tag type="info" size="small">{{ formatSec(currentPageAudio.duration_sec) }}</el-tag>
          </div>
          <div class="script-text">{{ currentPageAudio.script }}</div>
        </div>

        <!-- All pages script accordion -->
        <el-collapse class="all-scripts">
          <el-collapse-item title="全部页面脚本">
            <div v-for="pa in narration.page_audios" :key="pa.page_number" class="script-item">
              <div class="script-item-header">
                <span>第 {{ pa.page_number }} 页</span>
                <el-tag size="small">{{ pa.tone }}</el-tag>
                <el-tag type="info" size="small">{{ formatSec(pa.duration_sec) }}</el-tag>
              </div>
              <p class="script-body">{{ pa.script }}</p>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
    </div>

    <!-- Error state -->
    <el-alert v-if="narration && narration.status === 5" type="error"
      :title="`生成失败：${narration.error_msg || '未知错误'}`" show-icon />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoPlay } from '@element-plus/icons-vue'
import type { PitchPlan, PlanPage } from '@/api/pitchPlan'
import { narrationApi, type DemoNarration, type VoicePreset } from '@/api/narration'
import { useAuthStore } from '@/stores/auth'
import { useConversion } from '@/composables/useConversion'

const props = defineProps<{
  plan: PitchPlan | null
  pages: PlanPage[]
}>()

const auth = useAuthStore()
const { checkTrigger, trackEvent } = useConversion()

const voices = ref<VoicePreset[]>([])
const loadingVoices = ref(false)
const selectedVoiceId = ref('')
const selectedVoiceName = ref('专业男声')
const speed = ref(1.0)
const speedMarks = { 0.75: '0.75x', 1.0: '1x', 1.5: '1.5x' }

const narration = ref<DemoNarration | null>(null)
const generating = ref(false)
const genPct = ref(0)

// True only when a task is actively processing (1=脚本生成 2=合成 3=合并)
// status=0 means queued/pending — task may not have started yet, allow retry
const isActivelyGenerating = computed(() =>
  generating.value && narration.value != null && [1, 2, 3].includes(narration.value.status)
)

const currentPage = ref(1)
const fullAudioEl = ref<HTMLAudioElement | null>(null)

// WebSocket for progress
let ws: WebSocket | null = null

const statusLabel = computed(() => {
  const labels: Record<number, string> = {
    0: '等待中', 1: '生成脚本', 2: '合成音频', 3: '合并中', 4: '就绪', 5: '失败',
  }
  return narration.value ? labels[narration.value.status] ?? '' : ''
})

const statusTagType = computed(() => {
  if (!narration.value) return 'info'
  return { 4: 'success', 5: 'danger' }[narration.value.status] ?? 'warning'
})

const currentPageAudio = computed(() =>
  narration.value?.page_audios?.find(p => p.page_number === currentPage.value) ?? null
)

const canPlayPage = computed(() => !!currentPageAudio.value)

function pageAudio(pageNum: number) {
  return narration.value?.page_audios?.find(p => p.page_number === pageNum) ?? null
}

function formatSec(sec: number) {
  const m = Math.floor(sec / 60)
  const s = Math.round(sec % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function jumpToPage(pageNum: number) {
  const previousPage = currentPage.value
  currentPage.value = pageNum
  // T1: trigger upgrade when free user finishes page 3 and moves to page 4+
  if (previousPage === 3 && pageNum >= 4) {
    checkTrigger('T1', { page: pageNum })
  }
  // Seek full audio to start of this page
  if (fullAudioEl.value && narration.value?.page_audios) {
    const PAUSE = 0.8
    let offset = 0
    for (const pa of narration.value.page_audios) {
      if (pa.page_number === pageNum) break
      offset += pa.duration_sec + PAUSE
    }
    fullAudioEl.value.currentTime = offset
  }
}

function onTimeUpdate() {
  if (!fullAudioEl.value || !narration.value?.page_audios) return
  const t = fullAudioEl.value.currentTime
  const PAUSE = 0.8
  let offset = 0
  for (const pa of narration.value.page_audios) {
    if (t < offset + pa.duration_sec) {
      currentPage.value = pa.page_number
      return
    }
    offset += pa.duration_sec + PAUSE
  }
}

function onEnded() {
  // nothing needed
}

function playAll() {
  if (!fullAudioEl.value) return
  fullAudioEl.value.currentTime = 0
  fullAudioEl.value.play()
}

function playCurrentPage() {
  if (!fullAudioEl.value || !narration.value?.page_audios) return
  const PAUSE = 0.8
  let offset = 0
  for (const pa of narration.value.page_audios) {
    if (pa.page_number === currentPage.value) break
    offset += pa.duration_sec + PAUSE
  }
  fullAudioEl.value.currentTime = offset
  fullAudioEl.value.play()
}

async function handleGenerate() {
  if (!props.plan) return
  generating.value = true
  genPct.value = 0

  try {
    const res = await narrationApi.generate(props.plan.id, {
      voice_id: selectedVoiceId.value,
      voice_name: selectedVoiceName.value,
      speed: speed.value,
    })
    const narrationId = res.data.narration_id
    narration.value = null  // will be filled by WS updates
    connectWs(narrationId)
  } catch (e: any) {
    generating.value = false
    ElMessage.error(`生成失败：${e.response?.data?.detail || e.message}`)
  }
}

function connectWs(narrationId: number) {
  const tenantId = auth.user?.tenant_id
  if (!tenantId) return
  ws?.close()
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
  ws = new WebSocket(`${protocol}://${location.host}/ws/${tenantId}`)

  ws.onmessage = async (e) => {
    const evt = JSON.parse(e.data)
    if (evt.entity_type !== 'narration' || evt.entity_id !== narrationId) return
    genPct.value = evt.progress ?? 0

    if (evt.progress >= 100) {
      generating.value = false
      ws?.close()
      await refreshNarration()
    } else if (evt.stage?.startsWith('error:')) {
      generating.value = false
      ws?.close()
      await refreshNarration()
      ElMessage.error(`示范生成失败：${evt.stage.replace('error:', '').trim()}`)
    }
  }
}

async function refreshNarration() {
  if (!props.plan) return
  try {
    const res = await narrationApi.getLatest(props.plan.id)
    narration.value = res.data
  } catch (_) { /* no narration yet */ }
}

// Watch voice selection to sync name
watch(selectedVoiceId, (id) => {
  const v = voices.value.find(v => v.id === id)
  if (v) selectedVoiceName.value = v.name
})

onMounted(async () => {
  loadingVoices.value = true
  try {
    const [vRes] = await Promise.all([narrationApi.listVoices()])
    voices.value = vRes.data
    if (vRes.data.length) selectedVoiceId.value = vRes.data[0].id
  } finally {
    loadingVoices.value = false
  }
  await refreshNarration()
  // Only connect WS and show spinner when actively processing (not just queued)
  if (narration.value && [1, 2, 3].includes(narration.value.status)) {
    generating.value = true
    connectWs(narration.value.id)
  }
})

onUnmounted(() => { ws?.close() })
</script>

<style scoped>
/* Tab wrapper — normal flow, header shows at top */
.narration-tab {
  display: flex;
  flex-direction: column;
}

/* Sticky controls bar */
.narration-header {
  flex-shrink: 0;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
  padding: 12px 24px;
}
.narration-controls {
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
}
.label { font-size: 13px; color: var(--t-muted); white-space: nowrap; }
.speed-val {
  font-size: 13px; font-weight: 600; min-width: 32px;
  color: var(--accent);
}

/* Two-column layout — fixed height so columns scroll independently */
/* topbar(52) + tab-nav(44) + narration-header(~64) = 160px */
.narration-layout {
  display: flex;
  gap: 0;
  overflow: hidden;
  height: calc(100vh - 160px);
}

.thumb-strip {
  width: 160px;
  flex-shrink: 0;
  display: flex; flex-direction: column; gap: 8px;
  overflow-y: auto;
  height: 100%;
  padding: 16px 12px;
  border-right: 1px solid var(--border);
}
.thumb-item { cursor: pointer; border: 2px solid transparent; border-radius: 6px; padding: 4px;
  position: relative; transition: border-color .2s; }
.thumb-item.active { border-color: #409eff; background: #ecf5ff; }
.thumb-item:hover { border-color: #b3d8ff; }
.thumb-img { width: 100%; height: 80px; object-fit: contain; border-radius: 4px; }
.thumb-placeholder { width: 100%; height: 80px; display: flex; align-items: center; justify-content: center;
  background: #eee; border-radius: 4px; font-size: 20px; font-weight: 600; color: #aaa; }
.thumb-num { font-size: 11px; color: #909399; text-align: center; }
.thumb-dur { display: block; text-align: center; margin-top: 2px; }

.narration-main {
  flex: 1;
  display: flex; flex-direction: column; gap: 16px;
  overflow-y: auto;
  height: 100%;
  padding: 20px 24px;
}
/* Prevent flex-shrink from compressing children — let overflow-y: auto scroll instead */
.narration-main > * {
  flex-shrink: 0;
}

.full-player { background: #f5f7fa; border-radius: 8px; padding: 16px; }
.player-title { font-size: 14px; font-weight: 600; margin-bottom: 10px; display: flex; align-items: center; gap: 6px; }
.audio-ctrl { width: 100%; }
.player-actions { margin-top: 10px; display: flex; gap: 8px; }

.script-panel { border: 1px solid #e4e7ed; border-radius: 8px; padding: 16px; }
.script-header { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.page-label { font-weight: 600; }
.script-text { font-size: 14px; line-height: 1.8; color: #303133; white-space: pre-wrap; }

.all-scripts { border: 1px solid var(--border); border-radius: var(--radius-lg); overflow: hidden; }
/* Override Element Plus collapse content padding */
.all-scripts :deep(.el-collapse-item__header) {
  padding: 0 16px;
  font-size: 14px;
  font-weight: 600;
  color: var(--t-primary);
  background: var(--bg-content);
}
.all-scripts :deep(.el-collapse-item__content) {
  padding: 0;
}
.script-item {
  border-bottom: 1px solid var(--border);
  padding: 14px 16px;
}
.script-item:last-child { border-bottom: none; }
.script-item-header { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }
.script-body { font-size: 13px; color: var(--t-muted); line-height: 1.8; margin: 0; }
</style>
