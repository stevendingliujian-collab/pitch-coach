<template>
  <div class="page-container">
    <div class="page-header">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/projects' }">我的项目</el-breadcrumb-item>
        <el-breadcrumb-item>{{ task?.name }}</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <el-skeleton :loading="loading" animated :rows="8">
      <template #default>
        <el-tabs v-model="activeTab">
          <el-tab-pane label="讲解方案" name="plan">
            <PlanTab :task="task!" :plan="currentPlan" @plan-created="onPlanCreated" />
          </el-tab-pane>
          <el-tab-pane label="AI 示范讲解" name="narration">
            <NarrationTab :plan="currentPlan" :pages="currentPlan?.pages ?? []" />
          </el-tab-pane>
          <el-tab-pane label="排练记录" name="rehearsal">
            <RehearsalTab :task-id="taskId" :plan-id="currentPlan?.id ?? null" />
          </el-tab-pane>
          <el-tab-pane label="审核认证" name="review">
            <ReviewTab :task-id="taskId" :plan-id="currentPlan?.id ?? null" />
          </el-tab-pane>
        </el-tabs>
      </template>
    </el-skeleton>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { pitchTaskApi, type PitchTask } from '@/api/pitchTask'
import { pitchPlanApi, type PitchPlan } from '@/api/pitchPlan'
import PlanTab from '@/components/PlanTab.vue'
import NarrationTab from '@/components/NarrationTab.vue'
import RehearsalTab from '@/components/RehearsalTab.vue'
import ReviewTab from '@/components/ReviewTab.vue'

const route = useRoute()
const taskId = Number(route.params.id)
const task = ref<PitchTask | null>(null)
const currentPlan = ref<PitchPlan | null>(null)
const loading = ref(true)
const activeTab = ref('plan')

onMounted(async () => {
  try {
    const [taskRes, plansRes] = await Promise.all([
      pitchTaskApi.get(taskId),
      pitchPlanApi.listByTask(taskId),
    ])
    task.value = taskRes.data
    currentPlan.value = plansRes.data[0] ?? null
  } finally {
    loading.value = false
  }
})

function onPlanCreated(plan: PitchPlan) {
  currentPlan.value = plan
}
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 20px; }
</style>
