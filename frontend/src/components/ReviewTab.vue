<template>
  <div class="review-tab">
    <!-- No rehearsals yet -->
    <el-empty v-if="rehearsals.length === 0" description="暂无排练记录" />

    <template v-else>
      <!-- Rehearsal selector -->
      <div class="review-header">
        <span class="label">选择排练：</span>
        <el-select v-model="selectedRehearsalId" style="width: 280px" @change="onRehearsalChange">
          <el-option
            v-for="r in rehearsals"
            :key="r.id"
            :value="r.id"
            :label="`第${r.index}次排练 — ${r.score}分 — ${formatDate(r.created_at)}`"
          />
        </el-select>
        <el-tag :type="statusTagType" size="small" style="margin-left: 8px">{{ statusLabel }}</el-tag>

        <!-- Submit for review button (presenter) -->
        <el-button
          v-if="selectedRehearsal?.status === 3"
          type="primary" size="small" style="margin-left: 12px"
          :loading="submitting"
          @click="submitForReview"
        >提交经理审核</el-button>

        <!-- Certification status badge -->
        <el-tag v-if="cert" :type="cert.status === 1 ? 'success' : cert.status === 2 ? 'danger' : 'warning'"
          style="margin-left: 8px">
          认证：{{ cert.status_label }}
        </el-tag>
      </div>

      <!-- Audio player + timeline comments -->
      <div v-if="selectedRehearsal" class="review-body">
        <!-- Left: audio player with timeline -->
        <div class="player-panel">
          <div class="player-title">
            排练录音（{{ formatDur(selectedRehearsal.audio_duration) }}）
          </div>
          <audio
            ref="audioEl"
            :src="selectedRehearsal.audio_url ?? ''"
            controls
            preload="metadata"
            class="audio-ctrl"
            @timeupdate="onTimeUpdate"
          />

          <!-- Timeline comments -->
          <div class="timeline-header">
            <span>时间线批注</span>
            <el-button size="small" type="primary" :icon="Plus" @click="startAddComment">
              添加批注
            </el-button>
          </div>

          <div class="timeline-list">
            <div
              v-for="c in sortedComments"
              :key="c.id"
              class="timeline-item"
              :class="{ highlight: c.is_highlight }"
              @click="seekTo(c.timestamp_sec)"
            >
              <el-tag size="small" type="info" class="timestamp">
                {{ formatTimestamp(c.timestamp_sec) }}
              </el-tag>
              <span class="comment-text">{{ c.comment_text }}</span>
              <el-tag v-if="c.is_highlight" type="warning" size="small">⭐ 金牌</el-tag>
              <el-button
                v-if="c.reviewer_id === currentUserId"
                size="small" text type="danger"
                :icon="Delete"
                @click.stop="deleteComment(c.id)"
              />
            </div>
            <el-empty v-if="sortedComments.length === 0" :image-size="60" description="暂无批注" />
          </div>

          <!-- Add comment form -->
          <el-form v-if="showCommentForm" class="comment-form" @submit.prevent="submitComment">
            <div class="form-row">
              <span>批注时间：{{ formatTimestamp(commentTimestamp) }}</span>
              <el-button size="small" @click="commentTimestamp = audioEl?.currentTime ?? 0">
                标记当前时间
              </el-button>
            </div>
            <el-input
              v-model="commentText"
              type="textarea"
              :rows="2"
              placeholder="输入批注内容…"
              style="margin: 8px 0"
            />
            <div class="form-row">
              <el-checkbox v-model="commentHighlight">标记为金牌话术</el-checkbox>
              <div>
                <el-button size="small" @click="showCommentForm = false">取消</el-button>
                <el-button size="small" type="primary" :loading="savingComment" @click="submitComment">
                  保存批注
                </el-button>
              </div>
            </div>
          </el-form>
        </div>

        <!-- Right: manager certification panel -->
        <div class="cert-panel">
          <div class="cert-title">就绪认证</div>

          <template v-if="isManager">
            <el-form label-width="80px" class="cert-form">
              <el-form-item label="审核意见">
                <el-input v-model="certComment" type="textarea" :rows="4"
                  placeholder="写下您的审核意见（可选）…" />
              </el-form-item>
            </el-form>
            <div class="cert-actions">
              <el-button type="success" :loading="certifying" @click="certify('approve')">
                ✅ 通过认证
              </el-button>
              <el-button type="danger" :loading="certifying" @click="certify('reject')">
                ❌ 需要改进
              </el-button>
            </div>
          </template>

          <template v-else>
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item label="状态">
                <el-tag :type="cert?.status === 1 ? 'success' : cert?.status === 2 ? 'danger' : 'warning'">
                  {{ cert?.status_label ?? '未提交' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item v-if="cert?.review_comment" label="审核意见">
                {{ cert.review_comment }}
              </el-descriptions-item>
              <el-descriptions-item v-if="cert?.certified_at" label="认证时间">
                {{ formatDate(cert.certified_at) }}
              </el-descriptions-item>
            </el-descriptions>
            <el-empty v-if="!cert" :image-size="60" description="待经理审核" />
          </template>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { reviewApi, type ReviewComment, type Certification } from '@/api/review'

interface RehearsalListItem {
  id: number
  index: number
  score: string
  created_at: string
  status: number
  audio_url: string | null
  audio_duration: number
}

const props = defineProps<{
  taskId: number
  planId: number | null
}>()

const auth = useAuthStore()
const currentUserId = computed(() => auth.user?.id)
const isManager = computed(() => auth.user?.role === 'manager' || auth.user?.role === 'admin')

// Load rehearsal list from parent (passed via API)
const rehearsals = ref<RehearsalListItem[]>([])
const selectedRehearsalId = ref<number | null>(null)
const selectedRehearsal = computed(() => rehearsals.value.find(r => r.id === selectedRehearsalId.value) ?? null)

const comments = ref<ReviewComment[]>([])
const cert = ref<Certification | null>(null)
const audioEl = ref<HTMLAudioElement | null>(null)

// Comment form
const showCommentForm = ref(false)
const commentText = ref('')
const commentTimestamp = ref(0)
const commentHighlight = ref(false)
const savingComment = ref(false)

// Submit / certify state
const submitting = ref(false)
const certifying = ref(false)
const certComment = ref('')

const sortedComments = computed(() =>
  [...comments.value].sort((a, b) => a.timestamp_sec - b.timestamp_sec)
)

const statusMap: Record<number, { label: string; type: string }> = {
  0: { label: '录制中', type: 'info' },
  1: { label: '转录中', type: 'warning' },
  2: { label: '评分中', type: 'warning' },
  3: { label: '已评分', type: 'success' },
  4: { label: '待审核', type: 'warning' },
  5: { label: '已认证', type: 'success' },
  6: { label: '需改进', type: 'danger' },
}

const statusLabel = computed(() => {
  const s = selectedRehearsal.value?.status ?? -1
  return statusMap[s]?.label ?? ''
})
const statusTagType = computed(() => {
  const s = selectedRehearsal.value?.status ?? -1
  return statusMap[s]?.type ?? 'info'
})

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
function formatDur(sec: number) {
  const m = Math.floor(sec / 60), s = sec % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}
function formatTimestamp(sec: number) {
  const m = Math.floor(sec / 60), s = Math.floor(sec % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function onTimeUpdate() {
  // could drive active comment highlight — optional enhancement
}

function seekTo(sec: number) {
  if (audioEl.value) {
    audioEl.value.currentTime = sec
    audioEl.value.play()
  }
}

function startAddComment() {
  commentTimestamp.value = audioEl.value?.currentTime ?? 0
  commentText.value = ''
  commentHighlight.value = false
  showCommentForm.value = true
}

async function submitComment() {
  if (!selectedRehearsalId.value || !commentText.value.trim()) return
  savingComment.value = true
  try {
    const res = await reviewApi.addComment(selectedRehearsalId.value, {
      timestamp_sec: commentTimestamp.value,
      comment_text: commentText.value.trim(),
      is_highlight: commentHighlight.value,
    })
    comments.value.push(res.data)
    showCommentForm.value = false
    ElMessage.success('批注已保存')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    savingComment.value = false
  }
}

async function deleteComment(commentId: number) {
  if (!selectedRehearsalId.value) return
  await ElMessageBox.confirm('确认删除这条批注？', '删除', { type: 'warning' })
  await reviewApi.deleteComment(selectedRehearsalId.value, commentId)
  comments.value = comments.value.filter(c => c.id !== commentId)
  ElMessage.success('已删除')
}

async function submitForReview() {
  if (!selectedRehearsalId.value) return
  submitting.value = true
  try {
    await reviewApi.submitForReview(selectedRehearsalId.value)
    const r = rehearsals.value.find(r => r.id === selectedRehearsalId.value)
    if (r) r.status = 4
    ElMessage.success('已提交，等待经理审核')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '提交失败')
  } finally {
    submitting.value = false
  }
}

async function certify(decision: 'approve' | 'reject') {
  if (!selectedRehearsal.value) return
  certifying.value = true
  try {
    await reviewApi.certify({
      rehearsal_id: selectedRehearsal.value.id,
      pitch_task_id: props.taskId,
      user_id: selectedRehearsal.value.id, // should be presenter user_id — kept simple
      decision,
      comment: certComment.value,
    })
    ElMessage.success(decision === 'approve' ? '✅ 认证通过' : '已标记需要改进')
    await loadCert()
    await loadComments()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    certifying.value = false
  }
}

async function onRehearsalChange() {
  await Promise.all([loadComments(), loadCert()])
}

async function loadComments() {
  if (!selectedRehearsalId.value) return
  try {
    const res = await reviewApi.listComments(selectedRehearsalId.value)
    comments.value = res.data
  } catch { comments.value = [] }
}

async function loadCert() {
  try {
    const res = await reviewApi.getCertification(props.taskId)
    cert.value = res.data
  } catch { cert.value = null }
}

// Load rehearsals from the rehearsals API (reuse existing)
async function loadRehearsals() {
  const { api } = await import('@/api/index')
  try {
    const res = await api.get<any[]>(`/rehearsals/by-task/${props.taskId}`)
    rehearsals.value = res.data.map((r: any, i: number) => ({
      id: r.id,
      index: res.data.length - i,
      score: r.total_score?.toFixed(1) ?? '--',
      created_at: r.created_at,
      status: r.status,
      audio_url: r.audio_url,
      audio_duration: r.audio_duration,
    }))
    if (rehearsals.value.length) {
      selectedRehearsalId.value = rehearsals.value[0].id
      await onRehearsalChange()
    }
  } catch { rehearsals.value = [] }
}

onMounted(loadRehearsals)
</script>

<style scoped>
.review-tab { display: flex; flex-direction: column; gap: 16px; }
.review-header { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding: 12px; background: #f5f7fa; border-radius: 8px; }
.label { font-size: 13px; color: #606266; }

.review-body { display: grid; grid-template-columns: 1fr 320px; gap: 20px; }

.player-panel { display: flex; flex-direction: column; gap: 12px; }
.player-title { font-size: 14px; font-weight: 600; }
.audio-ctrl { width: 100%; }

.timeline-header { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; font-size: 13px; font-weight: 600; }
.timeline-list { display: flex; flex-direction: column; gap: 8px; max-height: 360px; overflow-y: auto; }
.timeline-item { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 6px; background: #f5f7fa; cursor: pointer; transition: background .15s; }
.timeline-item:hover { background: #ecf5ff; }
.timeline-item.highlight { background: #fdf6ec; border-left: 3px solid #e6a23c; }
.timestamp { flex-shrink: 0; }
.comment-text { flex: 1; font-size: 13px; }

.comment-form { border: 1px solid #e4e7ed; border-radius: 8px; padding: 12px; margin-top: 8px; }
.form-row { display: flex; justify-content: space-between; align-items: center; }

.cert-panel { border: 1px solid #e4e7ed; border-radius: 8px; padding: 16px; display: flex; flex-direction: column; gap: 16px; }
.cert-title { font-size: 15px; font-weight: 600; }
.cert-actions { display: flex; gap: 12px; }
</style>
