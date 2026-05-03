<template>
  <aside class="sidebar">
    <el-menu :default-active="activeMenu" router>
      <el-menu-item index="/projects">
        <el-icon><FolderOpened /></el-icon>
        <span>我的项目</span>
      </el-menu-item>
      <el-menu-item index="/daily-practice">
        <el-icon><Trophy /></el-icon>
        <span>每日微练习</span>
        <el-badge value="免费" type="success" class="menu-badge" />
      </el-menu-item>
      <el-menu-item index="/knowledge">
        <el-icon><Collection /></el-icon>
        <span>知识库</span>
      </el-menu-item>
    </el-menu>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { FolderOpened, Collection, Trophy } from '@element-plus/icons-vue'
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
.menu-badge { margin-left: 6px; }
</style>
