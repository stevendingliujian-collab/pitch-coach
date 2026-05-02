<template>
  <div :class="containerClass">
    <AppNavbar v-if="showNavbar" />
    <div class="main-layout">
      <AppSidebar v-if="showSidebar" />
      <div class="content-area">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppNavbar from '@/components/AppNavbar.vue'
import AppSidebar from '@/components/AppSidebar.vue'
import { useAppMode } from '@/composables/useAppMode'

const { showNavbar, showSidebar, containerClass } = useAppMode()
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
