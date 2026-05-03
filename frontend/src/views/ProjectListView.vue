<template>
  <div class="page-container">
    <div class="page-header">
      <h2>我的项目</h2>
      <el-button type="primary" :icon="Plus" @click="showCreate = true">新建项目</el-button>
    </div>

    <el-empty v-if="!loading && tasks.length === 0" description="还没有项目，点击右上角新建吧" />

    <div v-else class="task-grid">
      <el-card
        v-for="task in tasks"
        :key="task.id"
        class="task-card"
        shadow="hover"
        @click="router.push(`/projects/${task.id}`)"
      >
        <div class="task-card-header">
          <span class="urgency-dot" :class="urgencyClass(task)" />
          <span class="task-name">{{ task.name }}</span>
        </div>
        <div class="task-meta">
          <span v-if="task.customer_name">
            <el-icon><OfficeBuilding /></el-icon> {{ task.customer_name }}
          </span>
          <span v-if="task.bid_date">
            <el-icon><Calendar /></el-icon> 述标日期：{{ task.bid_date }}
          </span>
        </div>
        <div class="task-footer">
          <el-tag v-if="task.bid_date" :type="daysTagType(task.bid_date)" size="small">
            {{ daysLeft(task.bid_date) }}
          </el-tag>
          <el-tag v-if="task.result" :type="resultTagType(task.result)" size="small">
            {{ RESULT_LABELS[task.result] }}
          </el-tag>
        </div>
      </el-card>
    </div>

    <!-- Create project dialog -->
    <el-dialog v-model="showCreate" title="新建项目" width="520px">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-position="top">
        <el-form-item label="项目名称" prop="name">
          <el-input v-model="createForm.name" placeholder="如：苏州XX公司 MES 项目" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="客户名称">
              <el-input v-model="createForm.customer_name" placeholder="客户公司名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="客户行业">
              <el-select v-model="createForm.customer_industry" placeholder="选择行业">
                <el-option v-for="i in INDUSTRIES" :key="i" :label="i" :value="i" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="述标日期">
              <el-date-picker v-model="createForm.bid_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="述标时长（分钟）">
              <el-input-number v-model="createForm.bid_time_limit" :min="5" :max="120" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="招标要求摘要（选填）">
          <el-input v-model="createForm.bid_requirements" type="textarea" :rows="3" placeholder="粘贴评分标准、技术要求等" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { pitchTaskApi, type PitchTask } from '@/api/pitchTask'
import dayjs from 'dayjs'

const router = useRouter()
const tasks = ref<PitchTask[]>([])
const loading = ref(false)
const showCreate = ref(false)
const creating = ref(false)
const createFormRef = ref<FormInstance>()

const INDUSTRIES = ['非标自动化', '系统集成', '软件开发', '信息化', '工业互联网', '其他']
const RESULT_LABELS: Record<number, string> = { 1: '中标', 2: '未中标', 3: '弃标', 4: '流标' }

const createForm = ref({
  name: '', customer_name: '', customer_industry: '',
  bid_date: '', bid_time_limit: 30, bid_requirements: '',
})

const createRules: FormRules = {
  name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
}

onMounted(async () => {
  loading.value = true
  try { tasks.value = (await pitchTaskApi.list()).data } finally { loading.value = false }
})

async function handleCreate() {
  await createFormRef.value?.validate()
  creating.value = true
  try {
    const payload = { ...createForm.value, bid_date: createForm.value.bid_date || null }
    const res = await pitchTaskApi.create(payload)
    tasks.value.unshift(res.data)
    showCreate.value = false
    router.push(`/projects/${res.data.id}`)
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}

function daysLeft(bidDate: string): string {
  const diff = dayjs(bidDate).diff(dayjs(), 'day')
  if (diff < 0) return '已过期'
  if (diff === 0) return '今天述标'
  return `距述标 ${diff} 天`
}

function daysTagType(bidDate: string) {
  const diff = dayjs(bidDate).diff(dayjs(), 'day')
  if (diff < 0) return 'info'
  if (diff <= 3) return 'danger'
  if (diff <= 7) return 'warning'
  return 'success'
}

function urgencyClass(task: PitchTask) {
  if (!task.bid_date) return 'grey'
  const diff = dayjs(task.bid_date).diff(dayjs(), 'day')
  if (diff < 0) return 'grey'
  if (diff <= 3) return 'red'
  if (diff <= 7) return 'orange'
  return 'green'
}

function resultTagType(result: number) {
  return result === 1 ? 'success' : result === 2 ? 'danger' : 'info'
}
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-header h2 { font-size: 20px; font-weight: 600; color: #303133; }

.task-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }

.task-card { cursor: pointer; transition: transform 0.15s; }
.task-card:hover { transform: translateY(-2px); }

.task-card-header { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.task-name { font-weight: 600; font-size: 15px; color: #303133; }

.urgency-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.urgency-dot.red { background: #f56c6c; }
.urgency-dot.orange { background: #e6a23c; }
.urgency-dot.green { background: #67c23a; }
.urgency-dot.grey { background: #c0c4cc; }

.task-meta { display: flex; flex-direction: column; gap: 4px; color: #606266; font-size: 13px; margin-bottom: 12px; }
.task-meta span { display: flex; align-items: center; gap: 4px; }

.task-footer { display: flex; gap: 8px; }
</style>
