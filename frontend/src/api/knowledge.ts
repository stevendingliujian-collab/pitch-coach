import { api as apiClient } from './index'

export interface KnowledgeDocument {
  id: number
  tenant_id: number
  doc_type: string
  file_name: string
  file_url: string
  file_size: number | null
  chunk_count: number
  embedding_status: number
  embedding_status_label: string
  industry: string | null
  project_type: string | null
  tags: string[] | null
  description: string | null
  uploaded_by: number
  created_at: string
}

export interface DocumentListResponse {
  total: number
  page: number
  page_size: number
  items: KnowledgeDocument[]
}

export interface SearchHit {
  chunk_id: number | null
  doc_id: number | null
  doc_name: string | null
  rrf_score: number
  content: string
  heading: string | null
  page_number: number | null
  content_type: string
}

export interface SearchResponse {
  hits: SearchHit[]
  total: number
}

export const DOC_TYPE_LABELS: Record<string, string> = {
  bid_doc: '历史中标标书',
  lost_bid: '丢标标书',
  whitepaper: '白皮书',
  case_study: '案例研究',
  rubric_template: '评分表模板',
  company_profile: '公司简介',
  competitor_card: '竞品卡片',
  glossary: '术语表',
}

export const EMBEDDING_STATUS_LABELS: Record<number, string> = {
  0: '待处理',
  1: '处理中',
  2: '已完成',
  3: '失败',
}

export const knowledgeApi = {
  getUploadUrl(fileName: string, contentType: string) {
    return apiClient.post<{ upload_url: string; object_key: string }>(
      '/knowledge/documents/upload-url',
      { file_name: fileName, content_type: contentType }
    )
  },

  register(data: {
    object_key: string
    file_name: string
    file_size?: number
    doc_type: string
    industry?: string
    project_type?: string
    tags?: string[]
    description?: string
  }) {
    return apiClient.post<KnowledgeDocument>('/knowledge/documents', data)
  },

  list(params?: {
    doc_type?: string
    industry?: string
    embedding_status?: number
    page?: number
    page_size?: number
  }) {
    return apiClient.get<DocumentListResponse>('/knowledge/documents', { params })
  },

  get(id: number) {
    return apiClient.get<KnowledgeDocument>(`/knowledge/documents/${id}`)
  },

  delete(id: number) {
    return apiClient.delete(`/knowledge/documents/${id}`)
  },

  search(data: {
    query: string
    top_n?: number
    doc_type?: string
    industry?: string
  }) {
    return apiClient.post<SearchResponse>('/knowledge/search', data)
  },
}
