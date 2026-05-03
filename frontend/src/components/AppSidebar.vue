<template>
  <aside class="sidebar" :class="{ collapsed }">
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
      <button class="collapse-btn" @click="toggleCollapse" :title="collapsed ? '展开菜单' : '收起菜单'">
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
          <polyline v-if="!collapsed" points="10 3 5 8 10 13"/>
          <polyline v-else points="6 3 11 8 6 13"/>
        </svg>
      </button>
    </div>

    <!-- Nav -->
    <nav class="sidebar-nav">
      <div class="nav-section">
        <div class="nav-section-label">工作台</div>

        <router-link to="/projects" class="nav-item" :class="{ active: isActive('/projects') }" data-label="我的项目">
          <svg class="nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7">
            <rect x="2" y="3" width="7" height="8" rx="1.5"/>
            <rect x="11" y="3" width="7" height="4" rx="1.5"/>
            <rect x="11" y="9" width="7" height="8" rx="1.5"/>
            <rect x="2" y="13" width="7" height="4" rx="1.5"/>
          </svg>
          <span>我的项目</span>
        </router-link>

        <router-link to="/daily-practice" class="nav-item" :class="{ active: isActive('/daily-practice') }" data-label="每日微练习">
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

        <router-link to="/knowledge" class="nav-item" :class="{ active: isActive('/knowledge') }" data-label="知识库">
          <svg class="nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7">
            <rect x="3" y="2" width="14" height="16" rx="1.5"/>
            <line x1="7" y1="7" x2="13" y2="7"/>
            <line x1="7" y1="11" x2="13" y2="11"/>
            <line x1="7" y1="15" x2="10" y2="15"/>
          </svg>
          <span>知识库</span>
        </router-link>

        <router-link to="/golden-scripts" class="nav-item" :class="{ active: isActive('/golden-scripts') }" data-label="金牌话术库">
          <svg class="nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7">
            <polygon points="10 2 12.4 7.5 18.5 8.2 14 12.4 15.3 18.5 10 15.6 4.7 18.5 6 12.4 1.5 8.2 7.6 7.5"/>
          </svg>
          <span>金牌话术库</span>
        </router-link>
      </div>

      <div class="nav-section">
        <div class="nav-section-label">分析</div>

        <router-link to="/dashboard" class="nav-item" :class="{ active: isActive('/dashboard') }" data-label="进步看板">
          <svg class="nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7">
            <polyline points="2 14 7 9 11 13 18 5"/>
            <line x1="18" y1="5" x2="18" y2="9"/>
            <line x1="14" y1="5" x2="18" y2="5"/>
          </svg>
          <span>进步看板</span>
        </router-link>

        <router-link to="/evaluator" class="nav-item" :class="{ active: isActive('/evaluator') }" data-label="评委模拟">
          <svg class="nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7">
            <circle cx="10" cy="7" r="3.5"/>
            <path d="M4 17c0-3.3 2.7-6 6-6s6 2.7 6 6"/>
            <circle cx="16" cy="7" r="2.5" stroke-width="1.5"/>
            <line x1="16" y1="11" x2="16" y2="14"/>
            <line x1="14.5" y1="12.5" x2="17.5" y2="12.5"/>
          </svg>
          <span>评委模拟</span>
          <span class="nav-badge pro">专业版</span>
        </router-link>

        <router-link to="/post-mortem" class="nav-item" :class="{ active: isActive('/post-mortem') }" data-label="AI 复盘助手">
          <svg class="nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7">
            <circle cx="10" cy="10" r="7.5"/>
            <path d="M10 6.5v3.5l2.5 2.5"/>
            <line x1="7" y1="3" x2="7" y2="1.5"/>
            <line x1="13" y1="3" x2="13" y2="1.5"/>
          </svg>
          <span>AI 复盘助手</span>
          <span class="nav-badge elite">旗舰版</span>
        </router-link>

        <router-link to="/open-api" class="nav-item" :class="{ active: isActive('/open-api') }" data-label="Open API">
          <svg class="nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7">
            <rect x="2" y="3" width="16" height="11" rx="1.5"/>
            <path d="M6.5 7.5h.5M9 7.5h2M6.5 10.5h.5M9 10.5h5"/>
            <path d="M7 17h6M10 14v3"/>
          </svg>
          <span>Open API</span>
          <span class="nav-badge elite">旗舰版</span>
        </router-link>
      </div>

      <div class="nav-section">
        <div class="nav-section-label">成就</div>

        <router-link to="/achievements" class="nav-item" :class="{ active: isActive('/achievements') }" data-label="游戏化成就">
          <svg class="nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7">
            <path d="M10 2l2.1 5.3 5.6.7-4 3.9 1 5.5L10 14.7 5.3 17.4l1-5.5-4-3.9 5.6-.7z"/>
          </svg>
          <span>游戏化成就</span>
        </router-link>

        <router-link to="/ab-tests" class="nav-item" :class="{ active: isActive('/ab-tests') }" data-label="A/B 测试">
          <svg class="nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7">
            <path d="M3 4h6v12H3zM11 4h6v12h-6z"/>
            <path d="M6 10h8"/>
          </svg>
          <span>A/B 测试</span>
        </router-link>
      </div>

      <div class="nav-section">
        <div class="nav-section-label">账户</div>

        <router-link to="/pricing" class="nav-item" :class="{ active: isActive('/pricing') }" data-label="升级套餐">
          <svg class="nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7">
            <polygon points="10 2 12.4 7.5 18.5 8.2 14 12.4 15.3 18.5 10 15.6 4.7 18.5 6 12.4 1.5 8.2 7.6 7.5"/>
          </svg>
          <span>升级套餐</span>
        </router-link>

        <router-link to="/billing" class="nav-item" :class="{ active: isActive('/billing') }" data-label="账单管理">
          <svg class="nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7">
            <rect x="2" y="4" width="16" height="12" rx="2"/>
            <line x1="2" y1="8" x2="18" y2="8"/>
            <rect x="5" y="11" width="4" height="2" rx="0.5"/>
          </svg>
          <span>账单管理</span>
        </router-link>
      </div>

      <!-- Expand button shown only when collapsed -->
      <div v-if="collapsed" class="nav-item expand-btn" @click="toggleCollapse" title="展开菜单">
        <svg class="nav-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="6 3 11 8 6 13"/>
        </svg>
      </div>
    </nav>

    <!-- Usage bar -->
    <div class="sidebar-usage">
      <div class="usage-header">
        <span class="usage-label">本月项目用量</span>
        <span class="usage-count" :class="{ warn: usagePercent >= 80 }">
          {{ usedCount }}/{{ totalCount }}
          <span v-if="usagePercent >= 100">已用尽</span>
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
      <NotificationBell />
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
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import NotificationBell from '@/components/NotificationBell.vue'
import { api } from '@/api'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const collapsed = ref(localStorage.getItem('sidebar-collapsed') === 'true')

function toggleCollapse() {
  collapsed.value = !collapsed.value
}

function applySidebarWidth(v: boolean) {
  document.documentElement.style.setProperty('--sidebar-w', v ? '56px' : '220px')
}

watch(collapsed, (v) => {
  localStorage.setItem('sidebar-collapsed', String(v))
  applySidebarWidth(v)
})

onMounted(async () => {
  applySidebarWidth(collapsed.value)
  loadUsage()
  // Ensure user profile (including subscription_plan) is loaded
  if (auth.isLoggedIn && !auth.user) {
    await auth.fetchMe()
  }
})

function isActive(path: string) {
  return route.path === path || route.path.startsWith(path + '/')
}

const displayInitial = computed(() => {
  const name = auth.user?.name || auth.user?.email || '用'
  return name.charAt(0).toUpperCase()
})

const planLabel = computed(() => {
  const plan = (auth.user as any)?.subscription_plan
  if (!plan || plan === 'free') return '免费版'
  if (plan.startsWith('pro')) return '专业版'
  if (plan.startsWith('elite')) return '旗舰版'
  if (plan === 'enterprise') return '企业版'
  return plan
})

// Usage — real data from /subscription/usage
const _usedCount = ref(0)
const _totalCount = ref(3)
const usedCount = computed(() => _usedCount.value)
const totalCount = computed(() => _totalCount.value)
const usagePercent = computed(() => _totalCount.value > 0 ? (_usedCount.value / _totalCount.value) * 100 : 0)

async function loadUsage() {
  try {
    const res = await api.get<Record<string, { used: number; limit: number }>>('/subscription/usage')
    // Show pitch_tasks usage as the primary meter
    const tasksData = res.data?.pitch_tasks
    if (tasksData) {
      _usedCount.value = tasksData.used
      _totalCount.value = tasksData.limit
    }
  } catch {
    // Keep defaults if not logged in or quota check fails
  }
}

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
  transition: width 0.22s ease;
}

/* ── Collapse button ────────────────────────────── */
.collapse-btn {
  margin-left: auto;
  flex-shrink: 0;
  width: 24px; height: 24px;
  border-radius: 6px; border: none;
  background: rgba(255,255,255,0.06);
  color: rgba(255,255,255,0.35);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: all 0.15s;
}
.collapse-btn:hover { background: rgba(255,255,255,0.12); color: rgba(255,255,255,0.7); }
.collapse-btn svg { width: 12px; height: 12px; }

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

/* ── Collapsed state ────────────────────────────── */
.sidebar.collapsed .brand-text,
.sidebar.collapsed .nav-section-label,
.sidebar.collapsed .nav-item > span,
.sidebar.collapsed .nav-badge,
.sidebar.collapsed .sidebar-usage,
.sidebar.collapsed .user-info,
.sidebar.collapsed .notif-wrap,
.sidebar.collapsed .collapse-btn {
  display: none;
}

.sidebar.collapsed .sidebar-brand {
  padding: 16px 12px;
  justify-content: center;
  gap: 0;
}

.sidebar.collapsed .sidebar-nav {
  padding: 8px 6px 0;
}

.sidebar.collapsed .nav-item {
  padding: 9px;
  justify-content: center;
}

.sidebar.collapsed .sidebar-user {
  justify-content: center;
  gap: 0;
  padding: 10px 12px 14px;
}

/* Tooltip on hover when collapsed */
.sidebar.collapsed .nav-item[data-label] {
  position: relative;
}
.sidebar.collapsed .nav-item[data-label]:hover::after {
  content: attr(data-label);
  position: absolute;
  left: calc(100% + 8px);
  top: 50%;
  transform: translateY(-50%);
  background: rgba(15,15,19,0.95);
  color: rgba(255,255,255,0.9);
  font-size: 12px;
  font-weight: 500;
  padding: 5px 10px;
  border-radius: 6px;
  white-space: nowrap;
  z-index: 200;
  pointer-events: none;
  border: 1px solid rgba(255,255,255,0.08);
}
</style>
