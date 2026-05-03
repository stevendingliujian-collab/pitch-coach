<template>
  <nav class="mobile-bottom-nav">
    <router-link
      v-for="item in navItems"
      :key="item.to"
      :to="item.to"
      class="mobile-nav-item"
      :class="{ active: isActive(item.to) }"
    >
      <span class="mobile-nav-icon" v-html="item.icon"></span>
      <span class="mobile-nav-label">{{ item.label }}</span>
    </router-link>
  </nav>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

function isActive(path: string): boolean {
  return route.path === path || route.path.startsWith(path + '/')
}

const navItems = [
  {
    to: '/projects',
    label: '项目',
    icon: `<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8">
      <rect x="2" y="3" width="7" height="8" rx="1.5"/>
      <rect x="11" y="3" width="7" height="4" rx="1.5"/>
      <rect x="11" y="9" width="7" height="8" rx="1.5"/>
      <rect x="2" y="13" width="7" height="4" rx="1.5"/>
    </svg>`,
  },
  {
    to: '/daily-practice',
    label: '微练习',
    icon: `<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8">
      <circle cx="10" cy="10" r="7.5"/>
      <polyline points="10 6.5 10 10 12.5 12.5"/>
    </svg>`,
  },
  {
    to: '/evaluator',
    label: '评委',
    icon: `<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8">
      <circle cx="10" cy="7" r="3.5"/>
      <path d="M3 18c0-3.87 3.13-7 7-7s7 3.13 7 7"/>
    </svg>`,
  },
  {
    to: '/dashboard',
    label: '看板',
    icon: `<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8">
      <rect x="2" y="2" width="7" height="9" rx="1.5"/>
      <rect x="11" y="2" width="7" height="5" rx="1.5"/>
      <rect x="11" y="9" width="7" height="9" rx="1.5"/>
      <rect x="2" y="13" width="7" height="5" rx="1.5"/>
    </svg>`,
  },
  {
    to: '/knowledge',
    label: '知识库',
    icon: `<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8">
      <rect x="3" y="2" width="14" height="16" rx="1.5"/>
      <line x1="7" y1="6" x2="13" y2="6"/>
      <line x1="7" y1="9" x2="13" y2="9"/>
      <line x1="7" y1="12" x2="10" y2="12"/>
    </svg>`,
  },
]
</script>

<style scoped>
.mobile-bottom-nav {
  display: none;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 56px;
  background: #0F0F13;
  border-top: 1px solid rgba(255,255,255,0.08);
  z-index: 100;
  align-items: stretch;
  justify-content: space-around;
  /* safe area for iPhone notch */
  padding-bottom: env(safe-area-inset-bottom, 0);
}

@media (max-width: 600px) {
  .mobile-bottom-nav {
    display: flex;
  }
}

.mobile-nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: 3px;
  text-decoration: none;
  color: rgba(255,255,255,0.4);
  transition: color 0.15s;
  padding: 6px 4px;
  min-width: 0;
}

.mobile-nav-item.active {
  color: #6366F1;
}

.mobile-nav-item:active {
  background: rgba(255,255,255,0.04);
}

.mobile-nav-icon {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.mobile-nav-icon :deep(svg) {
  width: 22px;
  height: 22px;
}

.mobile-nav-label {
  font-size: 10px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}
</style>
