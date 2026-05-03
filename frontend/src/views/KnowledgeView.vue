<template>
  <div class="knowledge-page">
    <div class="page-header">
      <h2>知识库</h2>
      <p class="subtitle">上传历史标书、白皮书、案例等文档，AI 将在生成讲解方案时自动引用</p>
    </div>

    <!-- Upload + Search toolbar -->
    <div class="toolbar">
      <el-button type="primary" :icon="Upload" @click="showUploadDialog = true">
        上传文档
      </el-button>
      <el-input
        v-model="searchQuery"
        placeholder="搜索知识库内容…"
        :prefix-icon="Search"
        clearable
        style="width: 360px"
        @keyup.enter="doSearch"
        @clear="searchResults = null"
      />
      <el-button :icon="Search" @click="doSearch" :loading="searching">搜索</el-button>
    </div>

    <!-- Search results panel -->
    <div v-if="searchResults" class="search-results">
      <div class="section-title">
        搜索结果 <span class="count">（{{ searchResults.total }} 条）</span>
        <el-button link @click="searchResults = null">关闭</el-button>
      </div>
      <div v-if="searchResults.hits.length === 0" class="empty">未找到相关内容</div>
      <el-card
        v-for="hit in searchResults.hits"
        :key="hit.chunk_id ?? hit.rrf_score"
        class="hit-card"
      >
        <div class="hit-meta">
          <el-tag size="small" type="info">{{ hit.doc_name ?? '未知文档' }}</el-tag>
          <span v-if="hit.heading" class="hit-heading">{{ hit.heading }}</span>
          <span v-if="hit.page_number" class="hit-page">第 {{ hit.page_number }} 页</span>
          <span class="hit-score">相关度 {{ (hit.rrf_score * 1000).toFixed(1) }}</span>
        </div>
        <div class="hit-content">{{ hit.content }}</div>
      </el-card>
    </div>

    <!-- Filters -->
    <div class="filters" v-if="!searchResults">
      <el-select v-model="filterDocType" placeholder="文档类型" clearable style="width: 140px" @change="fetchDocs">
        <el-option v-for="(label, val) in DOC_TYPE_LABELS" :key="val" :label="label" :value="val" />
      </el-select>
      <el-select v-model="filterStatus" placeholder="嵌入状态" clearable style="width: 120px" @change="fetchDocs">
        <el-option label="待处理" :value="0" />
        <el-option label="处理中" :value="1" />
        <el-option label="已完成" :value="2" />
        <el-option label="失败" :value="3" />
      </el-select>
    </div>

    <!-- Document table -->
    <div v-if="!searchResults">
      <el-table
        v-loading="loading"
        :data="documents"
        row-key="id"
        style="width: 100%; margin-top: 16px"
      >
        <el-table-column label="文件名" prop="file_name" min-width="220">
          <template #default="{ row }">
            <span class="file-name">{{ row.file_name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="130">
          <template #default="{ row }">
            {{ DOC_TYPE_LABELS[row.doc_type] ?? row.doc_type }}
          </template>
        </el-table-column>
        <el-table-column label="行业" prop="industry" width="100" />
        <el-table-column label="分块数" prop="chunk_count" width="80" align="center" />
        <el-table-column label="嵌入状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.embedding_status)" size="small">
              {{ row.embedding_status_label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="大小" width="90" align="right">
          <template #default="{ row }">
            {{ row.file_size ? formatSize(row.file_size) : '—' }}
          </template>
        </el-table-column>
        <el-table-column label="上传时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" align="center">
          <template #default="{ row }">
            <el-popconfirm
              title="确认删除此文档？向量数据也将一并删除"
              @confirm="deleteDoc(row.id)"
            >
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="total > pageSize"
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        style="margin-top: 16px; justify-content: center"
        @current-change="fetchDocs"
      />
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
              <div class="el-upload__tip">支持 PDF、DOCX、PPTX、TXT、MD，每次上传 1 个文件</div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item label="行业">
          <el-input v-model="uploadForm.industry" placeholder="如：系统集成、软件开发" />
        </el-form-item>
        <el-form-item label="标签">
          <el-select
            v-model="uploadForm.tags"
            multiple
            filterable
            allow-create
            placeholder="输入后回车添加"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="uploadForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button
          type="primary"
          :loading="uploading"
          :disabled="!uploadForm.file || !uploadForm.doc_type"
          @click="submitUpload"
        >
          上传并开始解析
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload, Search, UploadFilled } from '@element-plus/icons-vue'
import axios from 'axios'
import {
  knowledgeApi,
  DOC_TYPE_LABELS,
  type KnowledgeDocument,
  type SearchResponse,
} from '@/api/knowledge'

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
const documents = ref<KnowledgeDocument[]>([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = 20

const filterDocType = ref<string | undefined>(undefined)
const filterStatus = ref<number | undefined>(undefined)

const searchQuery = ref('')
const searchResults = ref<SearchResponse | null>(null)
const searching = ref(false)

const showUploadDialog = ref(false)
const uploading = ref(false)
const uploadRef = ref()

const uploadForm = ref<{
  doc_type: string
  file: File | null
  industry: string
  tags: string[]
  description: string
}>({
  doc_type: '',
  file: null,
  industry: '',
  tags: [],
  description: '',
})

// ---------------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------------
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
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

onMounted(fetchDocs)

// ---------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------
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

// ---------------------------------------------------------------------------
// Upload flow: get presigned URL → PUT to MinIO → register
// ---------------------------------------------------------------------------
function onFileChange(file: any) {
  uploadForm.value.file = file.raw as File
}

function resetUpload() {
  uploadForm.value = { doc_type: '', file: null, industry: '', tags: [], description: '' }
  uploadRef.value?.clearFiles()
}

async function submitUpload() {
  const file = uploadForm.value.file
  if (!file || !uploadForm.value.doc_type) return

  uploading.value = true
  try {
    // 1. Get presigned URL
    const urlRes = await knowledgeApi.getUploadUrl(file.name, file.type || 'application/octet-stream')
    const { upload_url, object_key } = urlRes.data

    // 2. PUT file directly to MinIO
    await axios.put(upload_url, file, {
      headers: { 'Content-Type': file.type || 'application/octet-stream' },
    })

    // 3. Register document + trigger ingestion
    await knowledgeApi.register({
      object_key,
      file_name: file.name,
      file_size: file.size,
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

// ---------------------------------------------------------------------------
// Delete
// ---------------------------------------------------------------------------
async function deleteDoc(id: number) {
  try {
    await knowledgeApi.delete(id)
    ElMessage.success('已删除')
    fetchDocs()
  } catch {
    ElMessage.error('删除失败')
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function statusTagType(status: number): '' | 'success' | 'warning' | 'danger' | 'info' {
  const map: Record<number, '' | 'success' | 'warning' | 'danger' | 'info'> = {
    0: 'info',
    1: 'warning',
    2: 'success',
    3: 'danger',
  }
  return map[status] ?? ''
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function formatDate(iso: string): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}
</script>

<style scoped>
.knowledge-page {
  padding: 24px;
}
.page-header {
  margin-bottom: 20px;
}
.page-header h2 {
  margin: 0 0 4px;
  font-size: 20px;
}
.subtitle {
  color: #909399;
  font-size: 13px;
  margin: 0;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.filters {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
}
.section-title {
  font-weight: 600;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.count {
  font-weight: 400;
  color: #909399;
}
.search-results {
  margin-bottom: 24px;
}
.hit-card {
  margin-bottom: 10px;
}
.hit-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 12px;
  color: #909399;
}
.hit-heading {
  font-weight: 600;
  color: #303133;
}
.hit-page {
  margin-left: auto;
}
.hit-score {
  color: #409eff;
}
.hit-content {
  font-size: 13px;
  line-height: 1.6;
  color: #606266;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.file-name {
  word-break: break-all;
}
.empty {
  color: #c0c4cc;
  text-align: center;
  padding: 32px 0;
}
</style>
