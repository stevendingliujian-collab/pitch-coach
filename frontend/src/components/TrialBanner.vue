<template>
  <Teleport to="body">
    <Transition name="trial-slide">
      <div v-if="visible" class="trial-banner">
        <div class="trial-content">
          <span class="trial-icon">🎁</span>
          <div class="trial-text">
            <strong>限时体验：7 天专业版免费试用</strong>
            <span class="trial-sub">解锁无限排练、跟读背诵、评委模拟 — 无需信用卡</span>
          </div>
          <div class="trial-countdown" v-if="hoursLeft > 0">
            剩余 <strong>{{ hoursLeft }}</strong> 小时
          </div>
          <button class="trial-cta" :disabled="activating" @click="activateTrial">
            {{ activating ? '激活中…' : '立即体验' }}
          </button>
          <button class="trial-close" @click="dismiss" aria-label="关闭">✕</button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { subscriptionApi } from '@/api/subscription'
import { ElMessage } from 'element-plus'

const STORAGE_KEY = 'pc_trial_banner_dismissed'
const TRIAL_WINDOW_HOURS = 72  // show within first 72h after registration

const auth = useAuthStore()
const visible = ref(false)
const activating = ref(false)

const hoursLeft = computed(() => {
  if (!auth.user?.created_at) return 0
  const registered = new Date(auth.user.created_at).getTime()
  const deadline = registered + TRIAL_WINDOW_HOURS * 3600 * 1000
  const now = Date.now()
  return Math.max(0, Math.ceil((deadline - now) / 3600 / 1000))
})

function dismiss() {
  visible.value = false
  localStorage.setItem(STORAGE_KEY, '1')
}

async function activateTrial() {
  activating.value = true
  try {
    await subscriptionApi.startTrial()
    ElMessage.success('🎉 7天专业版试用已激活！享受完整功能吧～')
    dismiss()
  } catch (e: any) {
    const msg = e.response?.data?.detail || '激活失败，请稍后再试'
    ElMessage.error(msg)
  } finally {
    activating.value = false
  }
}

onMounted(async () => {
  if (localStorage.getItem(STORAGE_KEY)) return
  // Ensure user profile is loaded
  if (!auth.user) await auth.fetchMe()
  if (!auth.user?.created_at) return
  // Only show if within 72h window and user hasn't started trial
  if (hoursLeft.value > 0) {
    setTimeout(() => { visible.value = true }, 2000)
  }
})
</script>

<style scoped>
.trial-banner {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 8000;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  color: #fff;
  padding: 0 24px;
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.2);
}

.trial-content {
  max-width: 1200px;
  margin: 0 auto;
  height: 60px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.trial-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.trial-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.trial-text strong {
  font-size: 14px;
  font-weight: 700;
  color: #fff;
}

.trial-sub {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.65);
}

.trial-countdown {
  font-size: 13px;
  color: #fbbf24;
  flex-shrink: 0;
  white-space: nowrap;
}

.trial-countdown strong {
  font-size: 16px;
  font-weight: 800;
}

.trial-cta {
  background: linear-gradient(135deg, #409eff, #6c63ff);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 8px 20px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
  transition: opacity 0.2s;
  flex-shrink: 0;
}
.trial-cta:hover { opacity: 0.85; }

.trial-close {
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.5);
  font-size: 16px;
  cursor: pointer;
  padding: 4px 8px;
  transition: color 0.2s;
  flex-shrink: 0;
}
.trial-close:hover { color: #fff; }

/* Transition */
.trial-slide-enter-active,
.trial-slide-leave-active { transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1); }
.trial-slide-enter-from,
.trial-slide-leave-to { transform: translateY(100%); }
</style>
