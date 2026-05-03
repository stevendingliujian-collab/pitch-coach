<template>
  <div class="rehearsal-page" :class="{ fullscreen: isFullscreen }">
    <!-- Top bar -->
    <div class="top-bar">
      <div class="top-left">
        <el-button :icon="ArrowLeft" @click="goBack" size="small" text>返回</el-button>
        <span class="project-name">{{ taskName }}</span>
      </div>
      <div class="timer" :class="{ recording: recorder.state.value === 'recording' }">
        {{ formatTime(recorder.durationSec.value) }}
      </div>
      <div class="top-right">
        <el-button :icon="FullScreen" @click="toggleFullscreen" size="small" text />
      </div>
    </div>

    <!-- Main area -->
    <div class="main-area">
      <!-- Slide preview (left / center) -->
      <div class="slide-area">
        <div class="slide-container">
          <img v-if="currentThumbnail" :src="currentThumbnail" class="slide-img" />
          <div v-else class="slide-placeholder">
            <el-icon size="48"><Picture /></el-icon>
            <p>幻灯片 {{ currentPageIndex + 1 }}</p>
          </div>

          <!-- Page nav -->
          <div class="slide-nav">
            <el-button :icon="ArrowLeft" circle size="small"
              :disabled="currentPageIndex <= 0 || recorder.state.value === 'idle'"
              @click="prevPage" />
            <span class="page-indicator">{{ currentPageIndex + 1 }} / {{ pages.length }}</span>
            <el-button :icon="ArrowRight" circle size="small"
              :disabled="currentPageIndex >= pages.length - 1 || recorder.state.value === 'idle'"
              @click="nextPage" />
          </div>
        </div>
      </div>

      <!-- Hints panel (right, collapsible) -->
      <transition name="slide-hints">
        <div v-if="showHints && currentPage" class="hints-panel">
          <div class="hints-header">
            <span>讲解提示</span>
            <el-button :icon="Close" size="small" text @click="showHints = false" />
          </div>
          <div class="importance-tag">
            <el-tag :type="importanceType(currentPage.importance_level)" size="small">
              {{ importanceLabel(currentPage.importance_level) }}
            </el-tag>
            <span class="suggested-time">建议 {{ currentPage.suggested_duration }}秒</span>
          </div>
          <ul class="talking-points">
            <li v-for="(tp, i) in currentPage.talking_points" :key="i"
              :class="{ emphasis: tp.is_emphasis }">
              {{ tp.point }}
            </li>
          </ul>
          <div v-if="currentPage.transition_hint" class="transition-hint">
            <el-icon><ChatLineRound /></el-icon>
            {{ currentPage.transition_hint }}
          </div>
        </div>
      </transition>

      <!-- Show hints toggle -->
      <el-button v-if="!showHints && recorder.state.value === 'recording'"
        class="hints-toggle" size="small" circle
        @click="showHints = true">
        <el-icon><Document /></el-icon>
      </el-button>
    </div>

    <!-- Bottom recording bar -->
    <div class="recording-bar">
      <template v-if="recorder.state.value === 'idle'">
        <el-button type="primary" :icon="VideoPlay" round size="large"
          :loading="starting" @click="startRecording">
          开始排练
        </el-button>
      </template>

      <template v-else-if="recorder.state.value === 'recording'">
        <div class="recording-controls">
          <el-button :icon="VideoPause" round @click="recorder.pause()">暂停</el-button>
          <div class="recording-dot" />
          <el-button type="danger" :icon="CircleClose" round :loading="stopping"
            @click="stopAndSubmit">
            完成排练
          </el-button>
        </div>
      </template>

      <template v-else-if="recorder.state.value === 'paused'">
        <div class="recording-controls">
          <el-button type="primary" :icon="VideoPlay" round @click="recorder.resume()">继续</el-button>
          <el-button type="danger" :icon="CircleClose" round :loading="stopping"
            @click="stopAndSubmit">
            完成排练
          </el-button>
        </div>
      </template>

      <template v-else-if="recorder.state.value === 'stopped'">
        <div v-if="uploadProgress < 100" class="uploading">
          <el-progress :percentage="uploadProgress" :stroke-width="6" style="width:200px" />
          <span>上传中…</span>
        </div>
        <div v-else class="upload-done">
          <el-icon color="#67C23A"><SuccessFilled /></el-icon>
          <span>已提交，AI 正在评分…</span>
          <el-button type="primary" @click="goToReport" :loading="!rehearsalScored">
            {{ rehearsalScored ? '查看报告' : '评分中…' }}
          </el-button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft, ArrowRight, FullScreen, Close, VideoPlay, VideoPause,
  CircleClose, Document, Picture, ChatLineRound, SuccessFilled,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { pitchTaskApi } from '@/api/pitchTask'
import { pitchPlanApi, type PlanPage } from '@/api/pitchPlan'
import { rehearsalApi } from '@/api/rehearsal'
import { useRehearsalRecorder } from '@/composables/useRehearsalRecorder'

const route = useRoute()
const router = useRouter()
const taskId = Number(route.query.taskId)
const planId = route.query.planId ? Number(route.query.planId) : null

const taskName = ref('')
const pages = ref<PlanPage[]>([])
const currentPageIndex = ref(0)
const showHints = ref(true)
const isFullscreen = ref(false)

const starting = ref(false)
const stopping = ref(false)
const uploadProgress = ref(0)
const rehearsalId = ref<number | null>(null)
const objectKey = ref('')
const rehearsalScored = ref(false)
let pollingHandle: ReturnType<typeof setInterval> | null = null

const recorder = useRehearsalRecorder()

const currentPage = computed(() => pages.value[currentPageIndex.value] ?? null)
const currentThumbnail = computed(() => currentPage.value?.page_thumbnail_url ?? null)

onMounted(async () => {
  try {
    const [taskRes, planRes] = await Promise.all([
      pitchTaskApi.get(taskId),
      planId ? pitchPlanApi.get(planId) : null,
    ])
    taskName.value = taskRes.data.name
    if (planRes) pages.value = planRes.data.pages ?? []
  } catch { /* handled */ }
})

onUnmounted(() => {
  if (pollingHandle) clearInterval(pollingHandle)
  recorder.reset()
})

async function startRecording() {
  starting.value = true
  try {
    const res = await rehearsalApi.start(taskId, planId)
    rehearsalId.value = res.data.rehearsal_id
    objectKey.value = res.data.object_key
    // Store upload_url for later — keep it in a closure
    ;(window as any).__rehearsal_upload_url = res.data.upload_url

    await recorder.start(pages.value[0]?.page_number ?? 1)
  } catch (e: any) {
    const msg = e?.name === 'NotFoundError'
      ? '未找到麦克风，请连接麦克风后重试'
      : e?.name === 'NotAllowedError'
        ? '请允许浏览器使用麦克风'
        : `录音启动失败：${e?.message ?? e}`
    ElMessage.error(msg)
  } finally {
    starting.value = false
  }
}

function prevPage() {
  if (currentPageIndex.value <= 0) return
  currentPageIndex.value--
  recorder.turnPage(pages.value[currentPageIndex.value].page_number)
}

function nextPage() {
  if (currentPageIndex.value >= pages.value.length - 1) return
  currentPageIndex.value++
  recorder.turnPage(pages.value[currentPageIndex.value].page_number)
}

async function stopAndSubmit() {
  stopping.value = true
  try {
    const blob = await recorder.stop()
    const uploadUrl = (window as any).__rehearsal_upload_url as string

    await rehearsalApi.uploadAudio(uploadUrl, blob, (pct) => {
      uploadProgress.value = pct
    })
    uploadProgress.value = 100

    await rehearsalApi.complete(rehearsalId.value!, {
      object_key: objectKey.value,
      audio_duration: recorder.durationSec.value,
      page_timings: [...recorder.pageTimings.value],
    })

    startPolling()
  } catch (e: any) {
    ElMessage.error(`提交排练失败：${e?.response?.data?.detail ?? e?.message ?? e}`)
  } finally {
    stopping.value = false
  }
}

function startPolling() {
  pollingHandle = setInterval(async () => {
    if (!rehearsalId.value) return
    try {
      const res = await rehearsalApi.getStatus(rehearsalId.value)
      if (res.data.status >= 3) {
        rehearsalScored.value = true
        if (pollingHandle) clearInterval(pollingHandle)
      }
    } catch { /* ignore */ }
  }, 3000)
}

function goToReport() {
  router.push({ name: 'report', params: { id: rehearsalId.value } })
}

function goBack() {
  router.push({ name: 'projectDetail', params: { id: taskId } })
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen()
    isFullscreen.value = true
  } else {
    document.exitFullscreen()
    isFullscreen.value = false
  }
}

function formatTime(sec: number) {
  const m = Math.floor(sec / 60).toString().padStart(2, '0')
  const s = (sec % 60).toString().padStart(2, '0')
  return `${m}:${s}`
}

function importanceLabel(level: number) {
  const labels: Record<number, string> = { 1: '次要', 2: '普通', 3: '重要', 4: '关键', 5: '核心' }
  return labels[level] ?? '普通'
}

function importanceType(level: number): '' | 'success' | 'warning' | 'danger' | 'info' {
  if (level >= 5) return 'danger'
  if (level >= 4) return 'warning'
  if (level >= 3) return ''
  return 'info'
}
</script>

<style scoped>
.rehearsal-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #0f1117;
  color: #fff;
}

.rehearsal-page.fullscreen { position: fixed; inset: 0; z-index: 9999; }

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: #1a1d27;
  border-bottom: 1px solid #2d3142;
  flex-shrink: 0;
}

.top-left { display: flex; align-items: center; gap: 12px; }
.project-name { font-size: 14px; color: #a0aec0; }

.timer {
  font-size: 28px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: #4a5568;
  letter-spacing: 2px;
}
.timer.recording { color: #fc8181; }

.main-area {
  flex: 1;
  display: flex;
  overflow: hidden;
  position: relative;
}

.slide-area {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.slide-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  max-width: 900px;
  width: 100%;
}

.slide-img {
  width: 100%;
  border-radius: 8px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.5);
}

.slide-placeholder {
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #1a1d27;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #4a5568;
}

.slide-nav {
  display: flex;
  align-items: center;
  gap: 16px;
}

.page-indicator { font-size: 14px; color: #a0aec0; min-width: 60px; text-align: center; }

.hints-panel {
  width: 280px;
  background: #1a1d27;
  border-left: 1px solid #2d3142;
  padding: 16px;
  overflow-y: auto;
  flex-shrink: 0;
}

.hints-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-weight: 600;
}

.importance-tag {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.suggested-time { font-size: 12px; color: #a0aec0; }

.talking-points {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.talking-points li {
  font-size: 13px;
  color: #cbd5e0;
  padding: 6px 8px;
  background: #252836;
  border-radius: 4px;
  border-left: 3px solid #4a5568;
}

.talking-points li.emphasis {
  border-left-color: #f6ad55;
  color: #fbd38d;
  font-weight: 500;
}

.transition-hint {
  margin-top: 12px;
  font-size: 12px;
  color: #90cdf4;
  display: flex;
  gap: 6px;
  align-items: flex-start;
  background: #1e2a3a;
  padding: 8px;
  border-radius: 4px;
}

.hints-toggle {
  position: absolute;
  right: 16px;
  top: 50%;
  transform: translateY(-50%);
}

.slide-hints-enter-active,
.slide-hints-leave-active { transition: width 0.25s ease, opacity 0.25s ease; }
.slide-hints-enter-from,
.slide-hints-leave-to { width: 0; opacity: 0; overflow: hidden; }

.recording-bar {
  height: 80px;
  background: #1a1d27;
  border-top: 1px solid #2d3142;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  flex-shrink: 0;
}

.recording-controls { display: flex; align-items: center; gap: 16px; }

.recording-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #fc8181;
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.2; }
}

.uploading, .upload-done {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  color: #a0aec0;
}
</style>
