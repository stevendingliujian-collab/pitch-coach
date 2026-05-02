<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-logo">
        <el-icon size="36" color="#409eff"><TrendCharts /></el-icon>
        <h1>创建账号</h1>
        <p>开始您的述标训练之旅</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="handleRegister">
        <el-form-item label="公司名称" prop="company_name">
          <el-input v-model="form.company_name" placeholder="请输入公司名称" size="large" />
        </el-form-item>
        <el-form-item label="您的姓名" prop="name">
          <el-input v-model="form.name" placeholder="请输入姓名" size="large" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" type="email" placeholder="请输入邮箱" size="large" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="至少8位" size="large" show-password />
        </el-form-item>
        <el-button type="primary" size="large" :loading="loading" native-type="submit" style="width:100%;margin-top:8px">
          免费注册
        </el-button>
      </el-form>

      <div class="auth-footer">
        已有账号？<router-link to="/login">立即登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { authApi } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const formRef = ref<FormInstance>()
const loading = ref(false)
const form = ref({ company_name: '', name: '', email: '', password: '' })

const rules: FormRules = {
  company_name: [{ required: true, message: '请输入公司名称', trigger: 'blur' }],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  email: [{ required: true, type: 'email', message: '请输入有效邮箱', trigger: 'blur' }],
  password: [{ required: true, min: 8, message: '密码至少8位', trigger: 'blur' }],
}

async function handleRegister() {
  await formRef.value?.validate()
  loading.value = true
  try {
    const res = await authApi.register(form.value)
    auth.setToken(res.data.access_token)
    await auth.fetchMe()
    router.push('/projects')
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '注册失败')
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
