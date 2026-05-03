<template>
  <div class="notif-wrap" ref="wrapRef">
    <button class="notif-btn" @click="toggle" :title="`${notifications.length} 条通知`">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.7">
        <path d="M8 1.5a5 5 0 0 1 5 5v2.5l1.5 1.5H1.5L3 9V6.5a5 5 0 0 1 5-5z"/>
        <path d="M6.5 13.5a1.5 1.5 0 0 0 3 0"/>
      </svg>
      <span v-if="notifications.length" class="notif-count">{{ Math.min(notifications.length, 9) }}</span>
    </button>

    <Transition name="drop">
      <div v-if="open" class="notif-panel">
        <div class="notif-panel-header">
          <span class="panel-title">通知</span>
          <span class="panel-count" v-if="notifications.length">{{ notifications.length }} 条</span>
        </div>
        <div class="notif-list" v-if="notifications.length">
          <router-link
            v-for="(n, i) in notifications"
            :key="i"
            class="notif-item"
            :class="[`level-${n.level}`]"
            :to="n.action_url || '/'"
            @click="open = false"
          >
            <div class="notif-icon-wrap">
              <span class="notif-dot" :class="[`dot-${n.level}`]" />
            </div>
            <div class="notif-body">
              <div class="notif-title">{{ n.title }}</div>
              <div class="notif-msg">{{ n.message }}</div>
            </div>
          </router-link>
        </div>
        <div v-else class="notif-empty">暂无新通知</div>
      </div>
    </Transition>

    <!-- click-outside overlay -->
    <div v-if="open" class="notif-overlay" @click="open = false" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { notificationsApi, type Notification } from '@/api/notifications'

const open = ref(false)
const wrapRef = ref<HTMLElement | null>(null)
const notifications = ref<Notification[]>([])

function toggle() {
  open.value = !open.value
}

onMounted(async () => {
  try {
    const res = await notificationsApi.list()
    notifications.value = res.data
  } catch {}
})

// Refresh every 5 minutes
const interval = setInterval(async () => {
  try {
    const res = await notificationsApi.list()
    notifications.value = res.data
  } catch {}
}, 5 * 60 * 1000)

onBeforeUnmount(() => clearInterval(interval))
</script>

<style scoped>
.notif-wrap { position: relative; }

.notif-btn {
  width: 28px; height: 28px; border-radius: 7px; border: none;
  background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.5);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: all 0.15s; position: relative;
  flex-shrink: 0;
}
.notif-btn:hover { background: rgba(255,255,255,0.12); color: rgba(255,255,255,0.8); }
.notif-btn svg { width: 14px; height: 14px; }

.notif-count {
  position: absolute; top: -3px; right: -3px;
  min-width: 14px; height: 14px; border-radius: 7px;
  background: #EF4444; color: white;
  font-size: 9px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  padding: 0 3px;
  border: 1.5px solid #0F0F13;
}

/* Panel */
.notif-panel {
  position: absolute; left: calc(100% + 8px); bottom: 0;
  width: 300px; background: #1C1C2A;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
  z-index: 500;
  overflow: hidden;
}

.notif-panel-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px 10px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.panel-title { font-size: 13px; font-weight: 700; color: rgba(255,255,255,0.85); }
.panel-count { font-size: 11px; color: rgba(255,255,255,0.35); }

.notif-list { max-height: 360px; overflow-y: auto; }
.notif-item {
  display: flex; gap: 10px; padding: 10px 16px;
  text-decoration: none;
  border-bottom: 1px solid rgba(255,255,255,0.04);
  transition: background 0.1s;
}
.notif-item:hover { background: rgba(255,255,255,0.04); }
.notif-item:last-child { border-bottom: none; }

.notif-icon-wrap { padding-top: 3px; flex-shrink: 0; }
.notif-dot {
  width: 7px; height: 7px; border-radius: 50%; display: block;
}
.dot-urgent  { background: #EF4444; }
.dot-warning { background: #F59E0B; }
.dot-info    { background: #6366F1; }
.dot-success { background: #22C55E; }

.notif-body { flex: 1; min-width: 0; }
.notif-title { font-size: 12px; font-weight: 700; color: rgba(255,255,255,0.85); margin-bottom: 2px; }
.notif-msg { font-size: 11px; color: rgba(255,255,255,0.4); line-height: 1.4; }

.notif-empty { padding: 24px 16px; text-align: center; font-size: 13px; color: rgba(255,255,255,0.3); }

.notif-overlay { position: fixed; inset: 0; z-index: 499; }

/* Animation */
.drop-enter-active, .drop-leave-active { transition: opacity 0.15s, transform 0.15s; }
.drop-enter-from, .drop-leave-to { opacity: 0; transform: translateX(-8px); }
</style>
