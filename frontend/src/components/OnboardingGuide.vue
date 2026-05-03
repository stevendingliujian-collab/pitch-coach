<template>
  <Teleport to="body">
    <Transition name="ob-fade">
      <div v-if="visible" class="ob-overlay" @click.self="dismiss">
        <div class="ob-dialog">
          <!-- Progress dots -->
          <div class="ob-dots">
            <span
              v-for="n in 3"
              :key="n"
              class="ob-dot"
              :class="{ active: step === n - 1 }"
            />
          </div>

          <!-- Step content -->
          <Transition name="ob-slide" mode="out-in">
            <div :key="step" class="ob-step">
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
          </Transition>

          <!-- Actions -->
          <div class="ob-actions">
            <button v-if="step < 2" class="ob-btn-primary" @click="next">
              下一步 →
            </button>
            <button v-else class="ob-btn-primary ob-btn-finish" @click="finish">
              开始使用 🚀
            </button>
            <button class="ob-btn-skip" @click="dismiss">跳过引导</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const STORAGE_KEY = 'pc_onboarding_done'

const router = useRouter()
const visible = ref(false)
const step = ref(0)

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

function next() {
  if (step.value < 2) step.value++
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
    // Slight delay so the main page renders first
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
  gap: 0;
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
.ob-icon {
  font-size: 56px;
  margin-bottom: 16px;
  line-height: 1;
}
.ob-heading {
  font-size: 22px;
  font-weight: 700;
  color: #1d2129;
  margin-bottom: 10px;
}
.ob-desc {
  font-size: 14px;
  color: #6b7280;
  line-height: 1.7;
  margin-bottom: 20px;
}
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
.ob-tip {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: #374151;
}
.ob-tip-num {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

/* Actions */
.ob-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  width: 100%;
}
.ob-btn-primary {
  width: 100%;
  padding: 13px 0;
  background: #409eff;
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}
.ob-btn-primary:hover { background: #337ecc; }
.ob-btn-finish { background: linear-gradient(135deg, #409eff, #6c63ff); }
.ob-btn-finish:hover { background: linear-gradient(135deg, #337ecc, #5a52d5); }
.ob-btn-skip {
  background: none;
  border: none;
  color: #9ca3af;
  font-size: 13px;
  cursor: pointer;
  padding: 4px 8px;
  transition: color 0.2s;
}
.ob-btn-skip:hover { color: #6b7280; }

/* Transitions */
.ob-fade-enter-active,
.ob-fade-leave-active { transition: opacity 0.3s ease; }
.ob-fade-enter-from,
.ob-fade-leave-to { opacity: 0; }

.ob-slide-enter-active,
.ob-slide-leave-active { transition: all 0.25s ease; }
.ob-slide-enter-from { opacity: 0; transform: translateX(20px); }
.ob-slide-leave-to { opacity: 0; transform: translateX(-20px); }
</style>
