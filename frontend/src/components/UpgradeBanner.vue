<template>
  <Teleport to="body">
    <Transition name="ub-slide">
      <div v-if="visible" class="ub-banner" role="alert">
        <div class="ub-content">
          <span class="ub-icon">⚡</span>
          <div class="ub-text">
            <strong class="ub-title">{{ title }}</strong>
            <span class="ub-sub">{{ message }}</span>
          </div>
          <div v-if="usage" class="ub-usage">
            <div class="ub-progress-bar">
              <div
                class="ub-progress-fill"
                :style="{ width: Math.min(100, usage.pct) + '%' }"
              />
            </div>
            <span class="ub-usage-label">{{ usage.used }}/{{ usage.limit }}</span>
          </div>
          <button class="ub-cta" @click="openUpgrade">升级专业版</button>
          <button class="ub-close" @click="dismiss" aria-label="关闭">✕</button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useUpgradeBanner } from '@/composables/useUpgradeBanner'

const { visible, title, message, usage, dismiss, openUpgrade } = useUpgradeBanner()
</script>

<style scoped>
.ub-banner {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 7500;
  background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%);
  color: #fff;
  padding: 0 24px;
  box-shadow: 0 -4px 20px rgba(255, 107, 53, 0.35);
}

.ub-content {
  max-width: 1200px;
  margin: 0 auto;
  height: 64px;
  display: flex;
  align-items: center;
  gap: 14px;
}

.ub-icon {
  font-size: 22px;
  flex-shrink: 0;
}

.ub-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.ub-title {
  font-size: 14px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ub-sub {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ub-usage {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.ub-progress-bar {
  width: 80px;
  height: 6px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 3px;
  overflow: hidden;
}

.ub-progress-fill {
  height: 100%;
  background: #fff;
  border-radius: 3px;
  transition: width 0.4s ease;
}

.ub-usage-label {
  font-size: 12px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.9);
  white-space: nowrap;
}

.ub-cta {
  background: #fff;
  color: #ff6b35;
  border: none;
  border-radius: 8px;
  padding: 9px 18px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
  transition: opacity 0.2s;
  flex-shrink: 0;
}
.ub-cta:hover { opacity: 0.88; }

.ub-close {
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.6);
  font-size: 16px;
  cursor: pointer;
  padding: 4px 8px;
  transition: color 0.2s;
  flex-shrink: 0;
}
.ub-close:hover { color: #fff; }

/* Transition */
.ub-slide-enter-active,
.ub-slide-leave-active { transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
.ub-slide-enter-from,
.ub-slide-leave-to { transform: translateY(100%); }
</style>
