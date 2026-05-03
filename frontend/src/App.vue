<template>
  <div :class="containerClass">
    <AppNavbar v-if="showNavbar" />
    <div class="main-layout" :class="{ 'has-sidebar': showSidebar }">
      <AppSidebar v-if="showSidebar" />
      <div class="content-area">
        <router-view />
      </div>
    </div>
    <!-- Global overlays -->
    <OnboardingGuide v-if="isLoggedIn" />
    <TrialBanner v-if="isLoggedIn" />
    <UpgradeBanner />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppNavbar from '@/components/AppNavbar.vue'
import AppSidebar from '@/components/AppSidebar.vue'
import OnboardingGuide from '@/components/OnboardingGuide.vue'
import TrialBanner from '@/components/TrialBanner.vue'
import UpgradeBanner from '@/components/UpgradeBanner.vue'
import { useAppMode } from '@/composables/useAppMode'
import { useAuthStore } from '@/stores/auth'

const { showNavbar, showSidebar, containerClass } = useAppMode()
const auth = useAuthStore()
const isLoggedIn = computed(() => auth.isLoggedIn)
</script>

<style>
/* ── Design tokens ───────────────────────────────────────── */
:root {
  --bg-sidebar:    #0F0F13;
  --bg-content:    #F5F5F7;
  --bg-card:       #FFFFFF;
  --accent:        #6366F1;
  --accent-light:  rgba(99,102,241,0.12);
  --accent-dim:    rgba(99,102,241,0.08);
  --green:         #22C55E;
  --orange:        #F97316;
  --red:           #EF4444;
  --amber:         #F59E0B;
  --cyan:          #06B6D4;
  --t-primary:     #111827;
  --t-secondary:   #374151;
  --t-muted:       #6B7280;
  --t-faint:       #9CA3AF;
  --border:        #E5E7EB;
  --border-light:  #F3F4F6;
  --shadow-sm:     0 1px 2px rgba(0,0,0,0.05);
  --shadow-md:     0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04);
  --shadow-lg:     0 4px 16px rgba(0,0,0,0.10), 0 1px 4px rgba(0,0,0,0.06);
  --shadow-xl:     0 8px 32px rgba(0,0,0,0.14);
  --sidebar-w:     220px;
  --topbar-h:      52px;
  --radius-sm:     6px;
  --radius-md:     10px;
  --radius-lg:     14px;
}

/* ── Reset ───────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Inter', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: var(--bg-content);
  color: var(--t-primary);
  -webkit-font-smoothing: antialiased;
}

/* ── Layout ──────────────────────────────────────────────── */
.standalone-container { min-height: 100vh; display: flex; flex-direction: column; }
.embedded-container   { min-height: 100vh; }

.main-layout {
  display: flex;
  flex: 1;
  height: 100vh;
  overflow: hidden;
}

.main-layout.has-sidebar .content-area {
  height: 100vh;
  overflow: auto;
  background: var(--bg-content);
}

.content-area {
  flex: 1;
  overflow: auto;
  min-height: 100vh;
}

/* ── Shared page chrome ───────────────────────────────────── */
.v2-topbar {
  height: var(--topbar-h);
  display: flex;
  align-items: center;
  padding: 0 24px;
  gap: 10px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  position: sticky;
  top: 0;
  z-index: 10;
}
.v2-topbar-title { font-size: 16px; font-weight: 700; color: var(--t-primary); }
.v2-topbar-flex  { flex: 1; }
.v2-page         { display: flex; flex-direction: column; min-height: 100vh; }
.v2-content      { flex: 1; padding: 24px; }

/* ── Shared cards ─────────────────────────────────────────── */
.v2-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  border: 1px solid var(--border-light);
}

/* ── Buttons ──────────────────────────────────────────────── */
.btn-v2 {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 8px 14px; border-radius: var(--radius-sm);
  font-size: 13px; font-weight: 600; cursor: pointer;
  border: none; transition: all 0.15s; font-family: inherit;
}
.btn-v2-primary { background: var(--accent); color: #fff; }
.btn-v2-primary:hover { background: #5457e0; }
.btn-v2-ghost { background: var(--bg-card); color: var(--t-secondary); border: 1px solid var(--border); }
.btn-v2-ghost:hover { background: var(--bg-content); }

/* ── Stat cards ───────────────────────────────────────────── */
.stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 28px; }
.stat-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  padding: 18px 20px;
  border: 1px solid var(--border-light);
  box-shadow: var(--shadow-md);
}
.stat-label { font-size: 12px; color: var(--t-muted); font-weight: 500; margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between; }
.stat-dot   { width: 7px; height: 7px; border-radius: 50%; }
.stat-num   { font-size: 34px; font-weight: 800; color: var(--t-primary); line-height: 1; margin-bottom: 6px; letter-spacing: -1px; font-variant-numeric: tabular-nums; }
.stat-trend { font-size: 12px; color: var(--t-muted); display: flex; align-items: center; gap: 4px; }
.stat-trend.up   { color: var(--green); }
.stat-trend.fire { color: var(--orange); }

/* ── Responsive ───────────────────────────────────────────── */
@media (max-width: 900px) {
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 600px) {
  .stat-grid { grid-template-columns: 1fr; }
  :root { --sidebar-w: 0px; }
}
</style>
