<template>
  <div class="v2-page kn-page">
    <!-- Topbar -->
    <div class="v2-topbar">
      <span class="v2-topbar-title">知识库</span>
      <div class="v2-topbar-flex" />
      <!-- Search -->
      <div class="kn-search-wrap">
        <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" stroke-width="1.8">
          <circle cx="5.5" cy="5.5" r="4"/><line x1="9" y1="9" x2="12" y2="12"/>
        </svg>
        <input
          v-model="searchQuery"
          class="kn-search-input"
          placeholder="搜索知识库内容… ⌘K"
          @keyup.enter="doSearch"
        />
      </div>
      <!-- Filters -->
      <el-select v-model="filterDocType" placeholder="全部类型" clearable size="small" style="width:120px" @change="fetchDocs">
        <el-option v-for="(label, val) in DOC_TYPE_LABELS" :key="val" :label="label" :value="val" />
      </el-select>
      <button class="btn-v2 btn-v2-primary" @click="showUploadDialog = true">
        <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M6.5 1v8M3 5l3.5-4 3.5 4"/><rect x="1" y="10" width="11" height="2" rx="1"/>
        </svg>
        上传文档
      </button>
    </div>

    <div class="v2-content">

      <!-- Stats row -->
      <div class="kn-stats-row">
        <div class="kn-stat v2-card">
          <div class="kn-stat-icon indigo">
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7">
              <rect x="3" y="2" width="14" height="16" rx="1.5"/>
              <line x1="7" y1="7" x2="13" y2="7"/>
              <line x1="7" y1="11" x2="13" y2="11"/>
              <line x1="7" y1="15" x2="10" y2="15"/>
            </svg>
          </div>
          <div>
            <div class="kn-stat-val">{{ total }}</div>
            <div class="kn-stat-lbl">已上传文档</div>
          </div>
        </div>
        <div class="kn-stat v2-card">
          <div class="kn-stat-icon green">
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7">
              <rect x="2" y="2" width="7" height="7" rx="1"/><rect x="11" y="2" width="7" height="7" rx="1"/>
              <rect x="2" y="11" width="7" height="7" rx="1"/><rect x="11" y="11" width="7" height="7" rx="1"/>
            </svg>
          </div>
          <div>
            <div class="kn-stat-val">{{ totalChunks }}</div>
            <div class="kn-stat-lbl">知识块</div>
          </div>
        </div>
        <div class="kn-stat v2-card">
          <div class="kn-stat-icon amber">
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7">
              <circle cx="10" cy="10" r="7.5"/>
              <polyline points="10 6.5 10 10 12.5 12.5"/>
            </svg>
          </div>
          <div>
            <div class="kn-stat-val">{{ citationCount }}</div>
            <div class="kn-stat-lbl">本月引用次数</div>
          </div>
        </div>
      </div>

      <!-- Search results -->
      <div v-if="searchResults" class="kn-search-results v2-card">
        <div class="search-results-header">
          <span>搜索结果 · <strong>{{ searchResults.total }}</strong> 条</span>
          <button class="btn-v2 btn-v2-ghost" style="padding:4px 10px;font-size:12px" @click="searchResults = null">关闭</button>
        </div>
        <div v-if="searchResults.hits.length === 0" class="kn-empty">未找到相关内容</div>
        <div v-for="hit in searchResults.hits" :key="hit.chunk_id ?? hit.rrf_score" class="hit-item">
          <div class="hit-meta">
            <span class="hit-doc">{{ hit.doc_name ?? '未知文档' }}</span>
            <span v-if="hit.heading" class="hit-heading">{{ hit.heading }}</span>
            <span v-if="hit.page_number" class="hit-pg">第 {{ hit.page_number }} 页</span>
            <span class="hit-score">相关度 {{ (hit.rrf_score * 1000).toFixed(1) }}</span>
          </div>
          <div class="hit-content">{{ hit.content }}</div>
        </div>
      </div>

      <!-- Document card grid -->
      <div v-else>
        <div v-if="loading" class="kn-grid">
          <div v-for="n in 4" :key="n" class="kn-doc-card skeleton" />
        </div>
        <div v-else-if="documents.length === 0" class="kn-empty-state">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.25">
            <rect x="8" y="4" width="32" height="40" rx="3"/>
            <line x1="16" y1="16" x2="32" y2="16"/>
            <line x1="16" y1="24" x2="32" y2="24"/>
            <line x1="16" y1="32" x2="24" y2="32"/>
          </svg>
          <p>还没有文档</p>
          <p style="font-size:13px;color:var(--t-faint)">上传历史标书、白皮书、案例等文档</p>
          <button class="btn-v2 btn-v2-primary" style="margin-top:16px" @click="showUploadDialog = true">上传第一份文档</button>
        </div>
        <div v-else class="kn-grid">
          <div
            v-for="doc in documents"
            :key="doc.id"
            class="kn-doc-card v2-card"
          >
            <div class="kn-doc-icon" :class="docIconClass(doc.file_name)">
              <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7">
                <rect x="3" y="2" width="14" height="16" rx="1.5"/>
                <line x1="7" y1="7" x2="13" y2="7"/>
                <line x1="7" y1="11" x2="13" y2="11"/>
                <line x1="7" y1="15" x2="10" y2="15"/>
              </svg>
            </div>
            <div class="kn-doc-name">{{ doc.file_name }}</div>
            <div class="kn-doc-meta">
              <span>{{ doc.file_size ? formatSize(doc.file_size) : '—' }}</span>
              <span>·</span>
              <span>{{ doc.chunk_count ?? 0 }} 知识块</span>
            </div>
            <div class="kn-doc-tags">
              <span v-if="doc.doc_type" class="kn-tag type">{{ DOC_TYPE_LABELS[doc.doc_type] ?? doc.doc_type }}</span>
              <span v-if="doc.industry" class="kn-tag industry">{{ doc.industry }}</span>
            </div>
            <!-- Embed progress bar -->
            <div class="kn-embed-bar-wrap">
              <div class="kn-embed-bar" :class="`status-${doc.embedding_status}`" :style="{ width: embedPct(doc.embedding_status) + '%' }" />
            </div>
            <div class="kn-doc-footer">
              <span class="kn-status-label" :class="`status-txt-${doc.embedding_status}`">{{ doc.embedding_status_label }}</span>
              <el-popconfirm title="确认删除此文档？" @confirm="deleteDoc(doc.id)">
                <template #reference>
                  <button class="kn-del-btn">
                    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" stroke-width="1.8">
                      <polyline points="2 3 11 3"/><path d="M4 3V2h5v1"/><rect x="3" y="3" width="7" height="8" rx="1"/>
                      <line x1="5" y1="6" x2="5" y2="9"/><line x1="8" y1="6" x2="8" y2="9"/>
                    </svg>
                  </button>
                </template>
              </el-popconfirm>
            </div>
          </div>
        </div>

        <el-pagination
          v-if="total > pageSize"
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          style="margin-top: 20px; justify-content: center"
          @current-change="fetchDocs"
        />
      </div>
    </div>

    <!-- Upload dialog -->
    <el-dialog v-model="showUploadDialog" title="上传知识文档" width="480px" @close="resetUpload">
      <el-form :model="uploadForm" label-width="90px" @submit.prevent>
        <el-form-item label="文档类型" required>
          <el-select v-model="uploadForm.doc_type" placeholder="请选择">
            <el-option v-for="(label, val) in DOC_TYPE_LABELS" :key="val" :label="label" :value="val" />
          </el-select>
        </el-form-item>
        <el-form-item label="选择文件" required>
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            :on-change="onFileChange"
            :on-remove="() => { uploadForm.file = null }"
            accept=".pdf,.docx,.pptx,.txt,.md"
            drag
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖放文件到此处或 <em>点击上传</em></div>
            <template #tip>
              <div class="el-upload__tip">支持 PDF、DOCX、PPTX、TXT、MD</div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item label="行业">
          <el-input v-model="uploadForm.industry" placeholder="如：系统集成、软件开发" />
        </el-form-item>
        <el-form-item label="标签">
          <el-select v-model="uploadForm.tags" multiple filterable allow-create placeholder="输入后回车添加" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="uploadForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" :loading="uploading" :disabled="!uploadForm.file || !uploadForm.doc_type" @click="submitUpload">
          上传并开始解析
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import axios from 'axios'
import { knowledgeApi, DOC_TYPE_LABELS, type KnowledgeDocument, type SearchResponse } from '@/api/knowledge'

const documents  = ref<KnowledgeDocument[]>([])
const loading    = ref(false)
const total      = ref(0)
const currentPage = ref(1)
const pageSize   = 20

const filterDocType = ref<string | undefined>(undefined)
const filterStatus  = ref<number | undefined>(undefined)

const searchQuery   = ref('')
const searchResults = ref<SearchResponse | null>(null)
const searching     = ref(false)

const showUploadDialog = ref(false)
const uploading = ref(false)
const uploadRef = ref()

const uploadForm = ref<{ doc_type: string; file: File | null; industry: string; tags: string[]; description: string }>({
  doc_type: '', file: null, industry: '', tags: [], description: '',
})

// Derived stats
const totalChunks  = computed(() => documents.value.reduce((s, d) => s + (d.chunk_count ?? 0), 0))
const citationCount = computed(() => 12) // TODO: from analytics API

async function fetchDocs() {
  loading.value = true
  try {
    const res = await knowledgeApi.list({
      doc_type: filterDocType.value || undefined,
      embedding_status: filterStatus.value,
      page: currentPage.value,
      page_size: pageSize,
    })
    documents.value = res.data.items
    total.value     = res.data.total
  } finally {
    loading.value = false
  }
}

onMounted(fetchDocs)

async function doSearch() {
  if (!searchQuery.value.trim()) return
  searching.value = true
  try {
    const res = await knowledgeApi.search({ query: searchQuery.value, top_n: 10 })
    searchResults.value = res.data
  } finally {
    searching.value = false
  }
}

function onFileChange(file: any) { uploadForm.value.file = file.raw as File }

function resetUpload() {
  uploadForm.value = { doc_type: '', file: null, industry: '', tags: [], description: '' }
  uploadRef.value?.clearFiles()
}

async function submitUpload() {
  const file = uploadForm.value.file
  if (!file || !uploadForm.value.doc_type) return
  uploading.value = true
  try {
    const urlRes = await knowledgeApi.getUploadUrl(file.name, file.type || 'application/octet-stream')
    const { upload_url, object_key } = urlRes.data
    await axios.put(upload_url, file, { headers: { 'Content-Type': file.type || 'application/octet-stream' } })
    await knowledgeApi.register({
      object_key, file_name: file.name, file_size: file.size,
      doc_type: uploadForm.value.doc_type,
      industry: uploadForm.value.industry || undefined,
      tags: uploadForm.value.tags.length ? uploadForm.value.tags : undefined,
      description: uploadForm.value.description || undefined,
    })
    ElMessage.success('上传成功，后台正在解析文档…')
    showUploadDialog.value = false
    fetchDocs()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? '上传失败，请重试')
  } finally {
    uploading.value = false
  }
}

async function deleteDoc(id: number) {
  try {
    await knowledgeApi.delete(id)
    ElMessage.success('已删除')
    fetchDocs()
  } catch {
    ElMessage.error('删除失败')
  }
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function docIconClass(name: string): string {
  const ext = name.split('.').pop()?.toLowerCase() ?? ''
  if (['pdf'].includes(ext)) return 'icon-red'
  if (['pptx', 'ppt'].includes(ext)) return 'icon-orange'
  if (['docx', 'doc'].includes(ext)) return 'icon-blue'
  if (['txt', 'md'].includes(ext)) return 'icon-green'
  return 'icon-indigo'
}

function embedPct(status: number): number {
  return { 0: 0, 1: 55, 2: 100, 3: 100 }[status] ?? 0
}
</script>

<style scoped>
.kn-page { background: var(--bg-content); }

/* Search bar in topbar */
.kn-search-wrap {
  display: flex; align-items: center; gap: 7px;
  background: var(--bg-content); border: 1px solid var(--border);
  border-radius: var(--radius-sm); padding: 6px 12px;
  min-width: 240px;
}
.kn-search-input {
  border: none; background: none; outline: none; font-size: 13px;
  color: var(--t-primary); font-family: inherit; width: 100%;
}
.kn-search-input::placeholder { color: var(--t-faint); }

/* Stats row */
.kn-stats-row { display: flex; gap: 14px; margin-bottom: 24px; }
.kn-stat {
  display: flex; align-items: center; gap: 14px;
  padding: 16px 20px; flex: 1;
}
.kn-stat-icon {
  width: 40px; height: 40px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.kn-stat-icon svg { width: 20px; height: 20px; }
.kn-stat-icon.indigo { background: rgba(99,102,241,0.1); color: var(--accent); }
.kn-stat-icon.green  { background: rgba(34,197,94,0.1);  color: var(--green); }
.kn-stat-icon.amber  { background: rgba(245,158,11,0.1); color: var(--amber); }
.kn-stat-val { font-size: 28px; font-weight: 800; color: var(--t-primary); line-height: 1; }
.kn-stat-lbl { font-size: 12px; color: var(--t-muted); margin-top: 3px; }

/* Document grid */
.kn-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
}

/* Doc card */
.kn-doc-card { padding: 18px; cursor: pointer; transition: transform 0.15s, box-shadow 0.15s; }
.kn-doc-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-lg); }

.kn-doc-icon {
  width: 44px; height: 44px; border-radius: var(--radius-md);
  display: flex; align-items: center; justify-content: center; margin-bottom: 12px;
}
.kn-doc-icon svg { width: 22px; height: 22px; }
.icon-red    { background: rgba(239,68,68,0.1);  color: var(--red); }
.icon-orange { background: rgba(249,115,22,0.1); color: var(--orange); }
.icon-blue   { background: rgba(99,102,241,0.1); color: var(--accent); }
.icon-green  { background: rgba(34,197,94,0.1);  color: var(--green); }
.icon-indigo { background: rgba(99,102,241,0.1); color: var(--accent); }

.kn-doc-name {
  font-size: 13px; font-weight: 600; color: var(--t-primary); margin-bottom: 4px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.kn-doc-meta { font-size: 11px; color: var(--t-faint); display: flex; gap: 4px; margin-bottom: 8px; }
.kn-doc-tags { display: flex; gap: 5px; flex-wrap: wrap; margin-bottom: 10px; }
.kn-tag {
  padding: 2px 8px; border-radius: 10px; font-size: 10.5px; font-weight: 600;
}
.kn-tag.type     { background: var(--accent-dim); color: var(--accent); }
.kn-tag.industry { background: rgba(34,197,94,0.08); color: #16A34A; }

.kn-embed-bar-wrap { height: 3px; background: var(--border-light); border-radius: 2px; overflow: hidden; margin-bottom: 10px; }
.kn-embed-bar      { height: 100%; border-radius: 2px; transition: width 0.4s; }
.kn-embed-bar.status-0 { background: var(--t-faint); width: 0%; }
.kn-embed-bar.status-1 { background: var(--amber); }
.kn-embed-bar.status-2 { background: var(--green); }
.kn-embed-bar.status-3 { background: var(--red); }

.kn-doc-footer { display: flex; justify-content: space-between; align-items: center; }
.kn-status-label { font-size: 11px; font-weight: 600; }
.status-txt-0 { color: var(--t-faint); }
.status-txt-1 { color: var(--amber); }
.status-txt-2 { color: var(--green); }
.status-txt-3 { color: var(--red); }

.kn-del-btn {
  width: 26px; height: 26px; border-radius: 5px; border: none;
  background: none; color: var(--t-faint); cursor: pointer;
  display: flex; align-items: center; justify-content: center; transition: all 0.15s;
}
.kn-del-btn:hover { background: rgba(239,68,68,0.08); color: var(--red); }

/* Search results */
.kn-search-results { padding: 18px; margin-bottom: 20px; }
.search-results-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; font-size: 14px; color: var(--t-secondary); }
.hit-item { padding: 12px 0; border-bottom: 1px solid var(--border-light); }
.hit-item:last-child { border-bottom: none; }
.hit-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap; }
.hit-doc  { font-size: 11px; font-weight: 700; background: var(--accent-dim); color: var(--accent); padding: 2px 8px; border-radius: 10px; }
.hit-heading { font-size: 12px; font-weight: 600; color: var(--t-secondary); }
.hit-pg   { font-size: 11px; color: var(--t-faint); }
.hit-score { font-size: 11px; color: var(--t-faint); margin-left: auto; }
.hit-content { font-size: 13px; color: var(--t-secondary); line-height: 1.65; }

/* Empty / skeleton */
.kn-empty-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 64px 24px; text-align: center; color: var(--t-muted);
}
.kn-empty-state p { margin-top: 10px; font-size: 15px; font-weight: 600; color: var(--t-secondary); }
.kn-empty { text-align: center; padding: 24px; color: var(--t-faint); font-size: 13px; }
.skeleton {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%; animation: shimmer 1.2s infinite; min-height: 180px;
}
@keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
</style>
