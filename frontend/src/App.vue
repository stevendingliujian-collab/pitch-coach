<template>
  <div :class="containerClass">
    <AppNavbar v-if="showNavbar" />
    <div class="main-layout">
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
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #f5f7fa; }

.standalone-container { min-height: 100vh; display: flex; flex-direction: column; }
.embedded-container { min-height: 100vh; }

.main-layout {
  display: flex;
  flex: 1;
}

.content-area {
  flex: 1;
  overflow: auto;
  min-height: calc(100vh - 60px);
}
</style>
