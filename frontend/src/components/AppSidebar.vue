<template>
  <aside class="sidebar">
    <!-- Brand -->
    <div class="sidebar-brand">
      <div class="brand-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
        </svg>
      </div>
      <div class="brand-text">
        <span class="brand-name">述标教练</span>
        <span class="brand-sub">OTD AI · PITCH COACH</span>
      </div>
    </div>

    <!-- Nav -->
    <nav class="sidebar-nav">
      <div class="nav-section">
        <div class="nav-section-label">工作台</div>

        <router-link to="/projects" class="nav-item" :class="{ active: isActive('/projects') }">
          <svg class="nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7">
            <rect x="2" y="3" width="7" height="8" rx="1.5"/>
            <rect x="11" y="3" width="7" height="4" rx="1.5"/>
            <rect x="11" y="9" width="7" height="8" rx="1.5"/>
            <rect x="2" y="13" width="7" height="4" rx="1.5"/>
          </svg>
          <span>我的项目</span>
        </router-link>

        <router-link to="/daily-practice" class="nav-item" :class="{ active: isActive('/daily-practice') }">
          <svg class="nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7">
            <circle cx="10" cy="10" r="7.5"/>
            <polyline points="10 6.5 10 10 12.5 12.5"/>
          </svg>
          <span>每日微练习</span>
          <span class="nav-badge free">免费</span>
        </router-link>
      </div>

      <div class="nav-section">
        <div class="nav-section-label">资产库</div>

        <router-link to="/knowledge" class="nav-item" :class="{ active: isActive('/knowledge') }">
          <svg class="nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7">
            <rect x="3" y="2" width="14" height="16" rx="1.5"/>
            <line x1="7" y1="7" x2="13" y2="7"/>
            <line x1="7" y1="11" x2="13" y2="11"/>
            <line x1="7" y1="15" x2="10" y2="15"/>
          </svg>
          <span>知识库</span>
        </router-link>

        <div class="nav-item disabled">
          <svg class="nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7">
            <polygon points="10 2 12.4 7.5 18.5 8.2 14 12.4 15.3 18.5 10 15.6 4.7 18.5 6 12.4 1.5 8.2 7.6 7.5"/>
          </svg>
          <span>话术宝典</span>
          <span class="nav-badge pro">专业版</span>
        </div>
      </div>

      <div class="nav-section">
        <div class="nav-section-label">分析</div>

        <div class="nav-item disabled">
          <svg class="nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7">
            <polyline points="2 14 7 9 11 13 18 5"/>
            <line x1="18" y1="5" x2="18" y2="9"/>
            <line x1="14" y1="5" x2="18" y2="5"/>
          </svg>
          <span>进步看板</span>
          <span class="nav-badge pro">专业版</span>
        </div>
      </div>
    </nav>

    <!-- Usage bar -->
    <div class="sidebar-usage">
      <div class="usage-header">
        <span class="usage-label">本月项目用量</span>
        <span class="usage-count" :class="{ warn: usagePercent >= 100 }">
          {{ usedCount }}/{{ totalCount }} 已用尽
        </span>
      </div>
      <div class="usage-track">
        <div class="usage-fill" :style="{ width: Math.min(usagePercent, 100) + '%' }" :class="{ full: usagePercent >= 100 }" />
      </div>
    </div>

    <!-- User info -->
    <div class="sidebar-user">
      <div class="user-avatar">{{ displayInitial }}</div>
      <div class="user-info">
        <div class="user-name">{{ auth.displayName }}</div>
        <div class="user-plan">{{ planLabel }}</div>
      </div>
      <button class="user-settings" title="退出登录" @click="handleLogout">
        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6">
          <path d="M13 15l3-5-3-5"/>
          <line x1="16" y1="10" x2="7" y2="10"/>
          <path d="M7 4H4a1 1 0 00-1 1v10a1 1 0 001 1h3"/>
        </svg>
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

function isActive(path: string) {
  return route.path === path || route.path.startsWith(path + '/')
}

const displayInitial = computed(() => {
  const name = auth.user?.name || auth.user?.email || '用'
  return name.charAt(0).toUpperCase()
})

const planLabel = computed(() => {
  const plan = (auth.user as any)?.subscription_plan
  if (plan === 'pro') return '专业版'
  if (plan === 'elite') return '旗舰版'
  return '免费版'
})

// Usage — using a reasonable default; quota service will provide real data via 402 responses
const usedCount = computed(() => 3)
const totalCount = computed(() => 3)
const usagePercent = computed(() => (usedCount.value / totalCount.value) * 100)

function handleLogout() {
  auth.logout()
  router.push('/auth')
}
</script>

<style scoped>
/* ── Sidebar shell ──────────────────────────────── */
.sidebar {
  width: var(--sidebar-w);
  flex-shrink: 0;
  background: var(--bg-sidebar);
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  position: sticky;
  top: 0;
}

/* ── Brand ──────────────────────────────────────── */
.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 16px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  flex-shrink: 0;
}
.brand-icon {
  width: 32px; height: 32px; border-radius: 8px;
  background: var(--accent);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.brand-icon svg { width: 16px; height: 16px; color: #fff; }
.brand-text { display: flex; flex-direction: column; }
.brand-name { font-size: 14px; font-weight: 700; color: #fff; line-height: 1.2; }
.brand-sub  { font-size: 9.5px; color: rgba(255,255,255,0.28); letter-spacing: 0.5px; margin-top: 1px; }

/* ── Nav ────────────────────────────────────────── */
.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: 12px 10px 0;
  scrollbar-width: none;
}
.sidebar-nav::-webkit-scrollbar { display: none; }

.nav-section { margin-bottom: 18px; }
.nav-section-label {
  font-size: 10px; font-weight: 700; letter-spacing: 0.8px;
  color: rgba(255,255,255,0.22); text-transform: uppercase;
  padding: 0 8px; margin-bottom: 4px;
}

.nav-item {
  display: flex; align-items: center; gap: 9px;
  padding: 7px 8px; border-radius: 7px;
  font-size: 13px; font-weight: 500;
  color: rgba(255,255,255,0.52);
  cursor: pointer; transition: all 0.15s;
  text-decoration: none;
  position: relative;
  margin-bottom: 1px;
}
.nav-item:hover:not(.disabled) {
  background: rgba(255,255,255,0.06);
  color: rgba(255,255,255,0.82);
}
.nav-item.active {
  background: var(--accent-light);
  color: #fff;
}
.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0; top: 50%;
  transform: translateY(-50%);
  width: 3px; height: 18px;
  background: var(--accent);
  border-radius: 0 2px 2px 0;
}
.nav-item.disabled { cursor: not-allowed; opacity: 0.5; }

.nav-icon { width: 16px; height: 16px; flex-shrink: 0; }

.nav-badge {
  margin-left: auto;
  padding: 1px 7px;
  border-radius: 20px;
  font-size: 10px; font-weight: 700; letter-spacing: 0.2px;
}
.nav-badge.free { background: rgba(34,197,94,0.15); color: #22C55E; }
.nav-badge.pro  { background: rgba(99,102,241,0.15); color: #818CF8; }

/* ── Usage bar ──────────────────────────────────── */
.sidebar-usage {
  padding: 10px 14px 12px;
  border-top: 1px solid rgba(255,255,255,0.06);
  flex-shrink: 0;
}
.usage-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 6px;
}
.usage-label { font-size: 11px; color: rgba(255,255,255,0.28); font-weight: 500; }
.usage-count { font-size: 10px; color: rgba(255,255,255,0.32); }
.usage-count.warn { color: var(--red); }
.usage-track {
  height: 3px; border-radius: 2px;
  background: rgba(255,255,255,0.08);
  overflow: hidden;
}
.usage-fill {
  height: 100%; border-radius: 2px;
  background: linear-gradient(90deg, var(--accent), var(--orange));
  transition: width 0.4s ease;
}
.usage-fill.full { background: var(--red); }

/* ── User ───────────────────────────────────────── */
.sidebar-user {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px 14px;
  flex-shrink: 0;
}
.user-avatar {
  width: 28px; height: 28px; border-radius: 50%;
  background: var(--accent);
  color: #fff; font-size: 12px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.user-info { flex: 1; min-width: 0; }
.user-name {
  font-size: 12.5px; font-weight: 600; color: rgba(255,255,255,0.82);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.user-plan { font-size: 10.5px; color: rgba(255,255,255,0.3); margin-top: 1px; }
.user-settings {
  width: 28px; height: 28px; border-radius: 6px; border: none;
  background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.35);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: all 0.15s; flex-shrink: 0;
}
.user-settings:hover { background: rgba(255,255,255,0.1); color: rgba(255,255,255,0.7); }
.user-settings svg { width: 14px; height: 14px; }
</style>
