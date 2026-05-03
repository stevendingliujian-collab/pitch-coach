<template>
  <Teleport to="body">
    <Transition name="ob-fade">
      <div v-if="visible" class="ob-overlay" @click.self="dismiss">
        <div class="ob-dialog">
          <!-- Progress dots -->
          <div class="ob-dots">
            <span
              v-for="n in TOTAL_STEPS"
              :key="n"
              class="ob-dot"
              :class="{ active: step === n - 1 }"
            />
          </div>

          <!-- Step content -->
          <Transition name="ob-slide" mode="out-in">
            <!-- Step 0,2,3 — informational -->
            <div v-if="step !== 1" :key="step" class="ob-step">
              <div class="ob-icon">{{ steps[step].icon }}</div>
              <h2 class="ob-heading">{{ steps[step].title }}</h2>
              <p class="ob-desc">{{ steps[step].desc }}</p>
              <div class="ob-tips">
                <div v-for="(tip, i) in steps[step].tips" :key="i" class="ob-tip">
                  <span class="ob-tip-num">{{ i + 1 }}</span>
                  <span>{{ tip }}</span>
                </div>
              </div>
            </div>

            <!-- Step 1 — industry / role soft selection -->
            <div v-else key="profile" class="ob-step">
              <div class="ob-icon">🙋</div>
              <h2 class="ob-heading">个性化你的体验</h2>
              <p class="ob-desc">告诉我们你的行业和角色，AI 会优先推荐适合你的练习内容。<br><span style="color:#9ca3af;font-size:13px">完全可选，随时可跳过</span></p>

              <div class="ob-profile-section">
                <div class="ob-label">所在行业</div>
                <div class="ob-chips">
                  <span
                    v-for="ind in INDUSTRIES"
                    :key="ind"
                    class="ob-chip"
                    :class="{ selected: selectedIndustry === ind }"
                    @click="selectedIndustry = selectedIndustry === ind ? '' : ind"
                  >{{ ind }}</span>
                </div>
              </div>

              <div class="ob-profile-section">
                <div class="ob-label">我的角色</div>
                <div class="ob-chips">
                  <span
                    v-for="r in ROLES"
                    :key="r.value"
                    class="ob-chip"
                    :class="{ selected: selectedRole === r.value }"
                    @click="selectedRole = selectedRole === r.value ? '' : r.value"
                  >{{ r.label }}</span>
                </div>
              </div>
            </div>
          </Transition>

          <!-- Actions -->
          <div class="ob-actions">
            <button
              v-if="step < TOTAL_STEPS - 1"
              class="ob-btn-primary"
              :disabled="saving"
              @click="next"
            >
              {{ step === 1 && hasProfile ? '保存并继续 →' : '下一步 →' }}
            </button>
            <button v-else class="ob-btn-primary ob-btn-finish" @click="finish">
              开始使用 🚀
            </button>
            <button class="ob-btn-skip" @click="step === 1 ? skipProfile() : dismiss()">
              {{ step === 1 ? '跳过此步骤' : '跳过引导' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const STORAGE_KEY = 'pc_onboarding_done'
const TOTAL_STEPS = 4

const INDUSTRIES = ['系统集成', '非标自动化', '软件开发', '政务信息化', '医疗信息化', '其他']
const ROLES = [
  { label: '售前/商务', value: 'pre_sales' },
  { label: '技术支持', value: 'technical' },
  { label: '销售管理', value: 'sales_mgr' },
  { label: '项目经理', value: 'pm' },
]

const router = useRouter()
const auth = useAuthStore()
const visible = ref(false)
const step = ref(0)
const saving = ref(false)
const selectedIndustry = ref('')
const selectedRole = ref('')

const hasProfile = computed(() => !!selectedIndustry.value || !!selectedRole.value)

const steps = [
  {
    icon: '📊',
    title: '上传 PPT，一键生成述标方案',
    desc: '把你的投标 PPT 上传，AI 会自动分析内容，生成结构化的述标讲解方案。',
    tips: [
      '支持 PPTX 和 PDF 格式',
      'AI 按页提取核心要点',
      '方案生成约需 1-2 分钟',
    ],
  },
  // Step 1 rendered separately (profile form)
  {},
  {
    icon: '🎤',
    title: '对练排练，获得实时评分',
    desc: '选择任意方案页面，录音排练你的讲解。AI 实时分析语速、填充词和要点覆盖率。',
    tips: [
      '单页排练，5 分钟即可完成',
      '评分维度：时长 + 流利度 + 完整性',
      '反复练习，直到满意为止',
    ],
  },
  {
    icon: '🔥',
    title: '每日微练习，养成述标习惯',
    desc: '每天 5 分钟，系统化练习述标开场白、产品介绍、答疑话术。完全免费，无限次。',
    tips: [
      '按周轮换 5 种练习类型',
      '连续打卡解锁连击徽章',
      '查看历史得分追踪进步',
    ],
  },
]

async function saveProfile() {
  if (!hasProfile.value) return
  saving.value = true
  try {
    await authApi.updateProfile({
      industry: selectedIndustry.value || undefined,
      role: selectedRole.value || undefined,
    })
    await auth.fetchMe()
  } catch {
    // non-blocking — best effort
  } finally {
    saving.value = false
  }
}

async function next() {
  if (step.value === 1) {
    await saveProfile()
  }
  if (step.value < TOTAL_STEPS - 1) step.value++
}

function skipProfile() {
  step.value++
}

function dismiss() {
  visible.value = false
  localStorage.setItem(STORAGE_KEY, '1')
}

function finish() {
  visible.value = false
  localStorage.setItem(STORAGE_KEY, '1')
  router.push('/projects')
}

onMounted(() => {
  if (!localStorage.getItem(STORAGE_KEY)) {
    setTimeout(() => { visible.value = true }, 600)
  }
})
</script>

<style scoped>
.ob-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9000;
}

.ob-dialog {
  background: #fff;
  border-radius: 20px;
  padding: 40px 44px 32px;
  width: 480px;
  max-width: 92vw;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.18);
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* Dots */
.ob-dots {
  display: flex;
  gap: 8px;
  margin-bottom: 28px;
}
.ob-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ddd;
  transition: all 0.3s;
}
.ob-dot.active {
  background: #409eff;
  width: 24px;
  border-radius: 4px;
}

/* Step */
.ob-step {
  text-align: center;
  width: 100%;
}
.ob-icon { font-size: 56px; margin-bottom: 16px; line-height: 1; }
.ob-heading { font-size: 22px; font-weight: 700; color: #1d2129; margin-bottom: 10px; }
.ob-desc { font-size: 14px; color: #6b7280; line-height: 1.7; margin-bottom: 20px; }
.ob-tips {
  background: #f4f7fb;
  border-radius: 12px;
  padding: 16px 20px;
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 28px;
}
.ob-tip { display: flex; align-items: center; gap: 10px; font-size: 13px; color: #374151; }
.ob-tip-num {
  width: 22px; height: 22px; border-radius: 50%;
  background: #409eff; color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; flex-shrink: 0;
}

/* Profile step */
.ob-profile-section { text-align: left; width: 100%; margin-bottom: 20px; }
.ob-label { font-size: 13px; font-weight: 600; color: #374151; margin-bottom: 8px; }
.ob-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.ob-chip {
  padding: 6px 14px;
  border-radius: 20px;
  border: 1.5px solid #e5e7eb;
  font-size: 13px;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s;
  user-select: none;
}
.ob-chip:hover { border-color: #409eff; color: #409eff; }
.ob-chip.selected { border-color: #409eff; background: #ecf5ff; color: #409eff; font-weight: 600; }

/* Actions */
.ob-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  width: 100%;
  margin-top: 4px;
}
.ob-btn-primary {
  width: 100%; padding: 13px 0;
  background: #409eff; color: #fff;
  border: none; border-radius: 10px;
  font-size: 15px; font-weight: 600;
  cursor: pointer; transition: background 0.2s;
}
.ob-btn-primary:hover { background: #337ecc; }
.ob-btn-primary:disabled { opacity: 0.65; cursor: not-allowed; }
.ob-btn-finish { background: linear-gradient(135deg, #409eff, #6c63ff); }
.ob-btn-finish:hover { background: linear-gradient(135deg, #337ecc, #5a52d5); }
.ob-btn-skip {
  background: none; border: none;
  color: #9ca3af; font-size: 13px;
  cursor: pointer; padding: 4px 8px;
  transition: color 0.2s;
}
.ob-btn-skip:hover { color: #6b7280; }

/* Transitions */
.ob-fade-enter-active, .ob-fade-leave-active { transition: opacity 0.3s ease; }
.ob-fade-enter-from, .ob-fade-leave-to { opacity: 0; }

.ob-slide-enter-active, .ob-slide-leave-active { transition: all 0.25s ease; }
.ob-slide-enter-from { opacity: 0; transform: translateX(20px); }
.ob-slide-leave-to { opacity: 0; transform: translateX(-20px); }
</style>
