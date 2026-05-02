<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-logo">
        <el-icon size="36" color="#409eff"><TrendCharts /></el-icon>
        <h1>OTD AI 述标教练</h1>
        <p>提升投标演示质量，提高中标率</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="handleLogin">
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" type="email" placeholder="请输入邮箱" size="large" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" size="large" show-password />
        </el-form-item>
        <el-button type="primary" size="large" :loading="loading" native-type="submit" style="width:100%;margin-top:8px">
          登录
        </el-button>
      </el-form>

      <div class="auth-footer">
        还没有账号？<router-link to="/register">立即注册</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { authApi } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const form = ref({ email: '', password: '' })

const rules: FormRules = {
  email: [{ required: true, type: 'email', message: '请输入有效邮箱', trigger: 'blur' }],
  password: [{ required: true, min: 8, message: '密码至少8位', trigger: 'blur' }],
}

async function handleLogin() {
  await formRef.value?.validate()
  loading.value = true
  try {
    const res = await authApi.login(form.value)
    auth.setToken(res.data.access_token)
    await auth.fetchMe()
    const redirect = route.query.redirect as string || '/projects'
    router.push(redirect)
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #e8f4ff 0%, #f0f7ff 100%); }
.auth-card { width: 420px; background: #fff; border-radius: 12px; padding: 40px; box-shadow: 0 8px 32px rgba(0,0,0,0.08); }
.auth-logo { text-align: center; margin-bottom: 32px; }
.auth-logo h1 { font-size: 22px; font-weight: 700; margin: 12px 0 4px; color: #303133; }
.auth-logo p { color: #909399; font-size: 14px; }
.auth-footer { text-align: center; margin-top: 20px; color: #606266; font-size: 14px; }
.auth-footer a { color: #409eff; text-decoration: none; }
</style>
