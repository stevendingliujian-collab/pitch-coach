<template>
  <aside class="sidebar">
    <el-menu :default-active="activeMenu" router>
      <el-menu-item index="/projects">
        <el-icon><FolderOpened /></el-icon>
        <span>我的项目</span>
      </el-menu-item>
    </el-menu>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
const route = useRoute()
const activeMenu = computed(() => '/' + route.path.split('/')[1])
</script>

<style scoped>
.sidebar {
  width: 200px;
  background: #fff;
  border-right: 1px solid #e4e7ed;
  min-height: calc(100vh - 60px);
}
.el-menu { border-right: none; }
</style>
