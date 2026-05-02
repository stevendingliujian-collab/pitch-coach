<template>
  <header class="navbar">
    <div class="navbar-brand">
      <el-icon size="22" color="#409eff"><TrendCharts /></el-icon>
      <span>OTD AI 述标教练</span>
    </div>
    <div class="navbar-right">
      <el-dropdown @command="handleCommand">
        <span class="user-info">
          <el-avatar size="small" :src="auth.user?.avatar_url ?? undefined">{{ auth.user?.name?.[0] }}</el-avatar>
          <span>{{ auth.user?.name }}</span>
          <el-icon><ArrowDown /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
const auth = useAuthStore()
const router = useRouter()

function handleCommand(cmd: string) {
  if (cmd === 'logout') { auth.logout(); router.push('/login') }
}
</script>

<style scoped>
.navbar {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  position: sticky;
  top: 0;
  z-index: 100;
}
.navbar-brand { display: flex; align-items: center; gap: 8px; font-size: 16px; font-weight: 600; color: #303133; }
.navbar-right { display: flex; align-items: center; gap: 16px; }
.user-info { display: flex; align-items: center; gap: 8px; cursor: pointer; color: #606266; }
</style>
