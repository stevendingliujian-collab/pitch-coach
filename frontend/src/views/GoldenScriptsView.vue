<template>
  <div class="gs-view">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
          </svg>
          金牌话术库
        </h1>
        <span class="total-badge">共 {{ total }} 条</span>
      </div>
      <p class="page-desc">经理标记的精彩讲解片段，可在跟读/背诵模式中引用。</p>
    </div>

    <!-- Filters -->
    <div class="filter-bar">
      <input
        v-model="searchQuery"
        type="text"
        class="search-input"
        placeholder="搜索话术内容或标签…"
        @input="debouncedSearch"
      />
      <select v-model="filterTag" class="tag-select" @change="loadScripts">
        <option value="">所有标签</option>
        <option v-for="tag in allTags" :key="tag" :value="tag">{{ tag }}</option>
      </select>
    </div>

    <!-- Scripts list -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div> 加载中…
    </div>
    <div v-else-if="scripts.length === 0" class="empty-state">
      <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.25">
        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
      </svg>
      <p>还没有金牌话术</p>
      <p class="dim">在「审核认证」Tab 中，将排练时间点标记为「金牌」即可沉淀精彩片段。</p>
    </div>
    <div v-else class="scripts-list">
      <div v-for="script in filteredScripts" :key="script.id" class="script-card">
        <div class="script-header">
          <div class="script-meta">
            <span class="page-badge">第 {{ script.page_number }} 页</span>
            <span v-if="script.start_sec !== null" class="time-range">
              {{ formatTime(script.start_sec!) }} – {{ formatTime(script.end_sec ?? script.start_sec!) }}
            </span>
            <span class="usage-count">被引用 {{ script.usage_count }} 次</span>
          </div>
          <div class="script-actions">
            <button
              v-if="script.audio_clip_url"
              class="btn-play"
              @click="playAudio(script)"
            >
              <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
                <polygon points="2 1 10 6 2 11"/>
              </svg>
              播放
            </button>
            <button class="btn-copy" @click="copyTranscript(script)">
              {{ copiedId === script.id ? '已复制 ✓' : '复制' }}
            </button>
            <button class="btn-delete" @click="confirmDelete(script)">删除</button>
          </div>
        </div>

        <div class="script-transcript">{{ script.transcript }}</div>

        <div v-if="script.tags && script.tags.length" class="script-tags">
          <span v-for="tag in script.tags" :key="tag" class="tag-chip">{{ tag }}</span>
        </div>

        <div class="script-footer">
          <span class="dim">{{ formatDate(script.created_at) }}</span>
          <span v-if="script.rehearsal_id" class="dim">排练 #{{ script.rehearsal_id }}</span>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="total > pageSize" class="pagination">
      <button :disabled="page <= 1" class="page-btn" @click="changePage(page - 1)">上一页</button>
      <span>第 {{ page }} / {{ Math.ceil(total / pageSize) }} 页</span>
      <button :disabled="page >= Math.ceil(total / pageSize)" class="page-btn" @click="changePage(page + 1)">下一页</button>
    </div>

    <!-- Audio player -->
    <div v-if="playingUrl" class="floating-player">
      <audio :src="playingUrl" autoplay controls @ended="playingUrl = null" />
      <button class="close-player" @click="playingUrl = null">✕</button>
    </div>

    <!-- Confirm delete -->
    <Teleport to="body">
      <div v-if="deleteTarget" class="modal-overlay" @click.self="deleteTarget = null">
        <div class="modal modal-sm">
          <div class="modal-header"><h3>删除金牌话术</h3></div>
          <div class="modal-body">
            <p>确定要删除这条精彩片段吗？此操作不可恢复。</p>
            <p class="dim excerpt">{{ deleteTarget.transcript.slice(0, 80) }}…</p>
          </div>
          <div class="modal-footer">
            <button class="btn-cancel" @click="deleteTarget = null">取消</button>
            <button class="btn-danger" :disabled="deleting" @click="doDelete">{{ deleting ? '删除中…' : '确认删除' }}</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { goldenScriptsApi, type GoldenScript } from '@/api/goldenScripts'

// ─── State ────────────────────────────────────────────────────────────────────

const scripts = ref<GoldenScript[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)
const searchQuery = ref('')
const filterTag = ref('')
const playingUrl = ref<string | null>(null)
const copiedId = ref<number | null>(null)
const deleteTarget = ref<GoldenScript | null>(null)
const deleting = ref(false)

// ─── Computed ─────────────────────────────────────────────────────────────────

const allTags = computed(() => {
  const tags = new Set<string>()
  scripts.value.forEach(s => s.tags.forEach(t => tags.add(t)))
  return Array.from(tags).sort()
})

const filteredScripts = computed(() => {
  let list = scripts.value
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(s =>
      s.transcript.toLowerCase().includes(q) ||
      s.tags.some(t => t.toLowerCase().includes(q))
    )
  }
  if (filterTag.value) {
    list = list.filter(s => s.tags.includes(filterTag.value))
  }
  return list
})

// ─── Data loading ─────────────────────────────────────────────────────────────

async function loadScripts() {
  loading.value = true
  try {
    const res = await goldenScriptsApi.list({ page: page.value, page_size: pageSize })
    scripts.value = res.data.items
    total.value = res.data.total
  } catch { /* ignore */ } finally {
    loading.value = false
  }
}

function changePage(p: number) {
  page.value = p
  loadScripts()
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
function debouncedSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { }, 300)
}

// ─── Actions ──────────────────────────────────────────────────────────────────

function playAudio(script: GoldenScript) {
  playingUrl.value = script.audio_clip_url
}

async function copyTranscript(script: GoldenScript) {
  await navigator.clipboard.writeText(script.transcript)
  copiedId.value = script.id
  setTimeout(() => { copiedId.value = null }, 2000)
}

function confirmDelete(script: GoldenScript) {
  deleteTarget.value = script
}

async function doDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await goldenScriptsApi.delete(deleteTarget.value.id)
    deleteTarget.value = null
    await loadScripts()
  } finally {
    deleting.value = false
  }
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatTime(sec: number): string {
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function formatDate(iso: string | null): string {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

onMounted(loadScripts)
</script>

<style scoped>
.gs-view { padding: 28px 32px; max-width: 860px; }

/* Header */
.page-header { margin-bottom: 20px; }
.header-left { display: flex; align-items: center; gap: 12px; margin-bottom: 6px; }
.page-title { font-size: 20px; font-weight: 700; color: #1a1a2e; display: flex; align-items: center; gap: 8px; margin: 0; }
.page-title svg { color: #F59E0B; }
.total-badge { background: #FEF3C7; color: #92400E; padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: 600; }
.page-desc { color: #6b7280; font-size: 13px; margin: 0; }

/* Filter bar */
.filter-bar { display: flex; gap: 10px; margin-bottom: 20px; }
.search-input {
  flex: 1; padding: 8px 14px;
  border: 1px solid #d1d5db; border-radius: 8px;
  font-size: 13px; color: #1a1a2e;
}
.search-input:focus { outline: none; border-color: #6366F1; box-shadow: 0 0 0 2px rgba(99,102,241,0.12); }
.tag-select { padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 13px; color: #374151; }

/* Scripts */
.scripts-list { display: flex; flex-direction: column; gap: 12px; }
.script-card { background: white; border-radius: 12px; border: 1px solid #e5e7eb; padding: 16px; }
.script-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; margin-bottom: 10px; }
.script-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.page-badge { background: #ede9fe; color: #6d28d9; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 700; }
.time-range { font-size: 11px; color: #6b7280; font-family: monospace; }
.usage-count { font-size: 11px; color: #9ca3af; }
.script-actions { display: flex; gap: 6px; flex-shrink: 0; }

.btn-play { padding: 4px 10px; background: #F0FDF4; color: #16a34a; border: none; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 4px; }
.btn-copy { padding: 4px 10px; background: #eff6ff; color: #2563eb; border: none; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; }
.btn-delete { padding: 4px 10px; background: #fee2e2; color: #dc2626; border: none; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; }

.script-transcript { font-size: 14px; line-height: 1.7; color: #1a1a2e; margin-bottom: 10px; white-space: pre-wrap; }
.script-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
.tag-chip { background: #f3f4f6; color: #374151; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 500; }
.script-footer { display: flex; justify-content: space-between; font-size: 11px; }

/* Pagination */
.pagination { display: flex; align-items: center; justify-content: center; gap: 16px; margin-top: 24px; font-size: 13px; color: #6b7280; }
.page-btn { padding: 6px 14px; border: 1px solid #e5e7eb; border-radius: 6px; background: white; cursor: pointer; font-size: 13px; }
.page-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Floating audio player */
.floating-player { position: fixed; bottom: 80px; right: 24px; background: #1a1a2e; border-radius: 12px; padding: 12px; display: flex; align-items: center; gap: 10px; box-shadow: 0 8px 32px rgba(0,0,0,0.3); z-index: 100; }
.close-player { background: rgba(255,255,255,0.1); border: none; color: rgba(255,255,255,0.6); border-radius: 50%; width: 24px; height: 24px; cursor: pointer; font-size: 14px; }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; backdrop-filter: blur(4px); }
.modal { background: white; border-radius: 14px; max-width: 92vw; overflow-y: auto; box-shadow: 0 20px 60px rgba(0,0,0,0.2); }
.modal-sm { width: 380px; }
.modal-header { padding: 20px 24px 0; }
.modal-header h3 { font-size: 17px; font-weight: 700; color: #1a1a2e; margin: 0; }
.modal-body { padding: 12px 24px; }
.modal-body p { margin: 0 0 8px; font-size: 14px; line-height: 1.6; color: #374151; }
.excerpt { font-style: italic; }
.modal-footer { padding: 12px 24px 20px; display: flex; justify-content: flex-end; gap: 10px; }
.btn-cancel { padding: 8px 16px; background: #f3f4f6; color: #374151; border: none; border-radius: 8px; font-size: 13px; cursor: pointer; }
.btn-danger { padding: 8px 16px; background: #dc2626; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-danger:disabled { opacity: 0.6; cursor: not-allowed; }

/* Loading & empty */
.loading-state { display: flex; align-items: center; gap: 10px; color: #6b7280; padding: 40px; justify-content: center; }
.spinner { width: 20px; height: 20px; border: 2px solid #e5e7eb; border-top-color: #6366F1; border-radius: 50%; animation: spin 0.6s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.empty-state { display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 60px 20px; text-align: center; color: #6b7280; }
.dim { color: #9ca3af; font-size: 12px; }

/* Mobile */
@media (max-width: 600px) {
  .gs-view { padding: 16px; }
  .script-header { flex-direction: column; gap: 8px; }
  .script-actions { flex-wrap: wrap; }
}
</style>
