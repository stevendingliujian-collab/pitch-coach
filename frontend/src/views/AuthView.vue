<template>
  <div class="auth-page">
    <div class="auth-card">
      <!-- Logo -->
      <div class="auth-logo">
        <el-icon size="36" color="#409eff"><TrendCharts /></el-icon>
        <h1>OTD AI 述标教练</h1>
        <p>提升投标演示质量，提高中标率</p>
      </div>

      <!-- Tab: WeChat / Phone / Email -->
      <el-tabs v-model="activeTab" class="auth-tabs" stretch>
        <!-- WeChat QR tab -->
        <el-tab-pane name="wechat">
          <template #label>
            <span class="tab-label wechat-label">
              <el-icon><ChatDotRound /></el-icon> 微信扫码
            </span>
          </template>
          <WechatQrCode @success="handleTokenResponse" />
        </el-tab-pane>

        <!-- Phone + SMS tab -->
        <el-tab-pane name="phone" label="手机号验证码">
          <template #label>
            <span class="tab-label">
              <el-icon><Iphone /></el-icon> 手机号
            </span>
          </template>
          <div style="margin-top:16px">
            <PhoneVerification
              :loading="phoneLoading"
              @submit="handlePhoneLogin"
            />
          </div>
        </el-tab-pane>

        <!-- Email + password (folded) -->
        <el-tab-pane name="email">
          <template #label>
            <span class="tab-label">
              <el-icon><Message /></el-icon> 邮箱
            </span>
          </template>
          <el-form
            ref="emailFormRef"
            :model="emailForm"
            :rules="emailRules"
            label-position="top"
            style="margin-top:16px"
            @submit.prevent="handleEmailAuth"
          >
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="emailForm.email" type="email" placeholder="请输入邮箱" size="large" />
            </el-form-item>
            <el-form-item label="密码" prop="password">
              <el-input v-model="emailForm.password" type="password" placeholder="请输入密码（≥8位）" size="large" show-password />
            </el-form-item>
            <!-- Name field only when registering -->
            <el-form-item v-if="emailMode === 'register'" label="姓名（选填）">
              <el-input v-model="emailForm.name" placeholder="您的姓名" size="large" />
            </el-form-item>

            <el-button
              type="primary"
              size="large"
              :loading="emailLoading"
              native-type="submit"
              style="width:100%;margin-top:4px"
            >
              {{ emailMode === 'login' ? '登录' : '注册' }}
            </el-button>
            <div class="email-switch">
              <template v-if="emailMode === 'login'">
                还没账号？<el-button type="primary" link @click="emailMode = 'register'">免费注册</el-button>
              </template>
              <template v-else>
                已有账号？<el-button type="primary" link @click="emailMode = 'login'">去登录</el-button>
              </template>
            </div>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <!-- Enterprise login links -->
      <div class="enterprise-links">
        <span>企业用户：</span>
        <el-button type="primary" link size="small" @click="showEnterpriseInfo">企业微信</el-button>
        <el-divider direction="vertical" />
        <el-button type="primary" link size="small" @click="showEnterpriseInfo">飞书</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { authApi, type TokenResponse } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import WechatQrCode from '@/components/WechatQrCode.vue'
import PhoneVerification from '@/components/PhoneVerification.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const activeTab = ref<'wechat' | 'phone' | 'email'>('phone')
const phoneLoading = ref(false)
const emailLoading = ref(false)
const emailMode = ref<'login' | 'register'>('login')

// Email form
const emailFormRef = ref<FormInstance>()
const emailForm = ref({ email: '', password: '', name: '' })
const emailRules: FormRules = {
  email: [{ required: true, type: 'email', message: '请输入有效邮箱', trigger: 'blur' }],
  password: [{ required: true, min: 8, message: '密码至少 8 位', trigger: 'blur' }],
}

function handleTokenResponse(tokenRes: TokenResponse) {
  auth.applyTokenResponse(tokenRes)
  afterLogin()
}

async function afterLogin() {
  await auth.fetchMe()
  const redirect = route.query.redirect as string || '/projects'
  router.push(redirect)
}

async function handlePhoneLogin(phone: string, code: string) {
  phoneLoading.value = true
  try {
    const res = await authApi.smsLogin(phone, code)
    handleTokenResponse(res.data)
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '验证码错误')
  } finally {
    phoneLoading.value = false
  }
}

async function handleEmailAuth() {
  await emailFormRef.value?.validate()
  emailLoading.value = true
  try {
    if (emailMode.value === 'login') {
      const res = await authApi.login({ email: emailForm.value.email, password: emailForm.value.password })
      handleTokenResponse(res.data)
    } else {
      const res = await authApi.register({
        email: emailForm.value.email,
        password: emailForm.value.password,
        name: emailForm.value.name || undefined,
      })
      handleTokenResponse(res.data)
    }
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || (emailMode.value === 'login' ? '登录失败' : '注册失败'))
  } finally {
    emailLoading.value = false
  }
}

function showEnterpriseInfo() {
  ElMessage.info('企业IM 登录即将上线，请使用手机号或邮箱登录')
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #e8f4ff 0%, #f0f7ff 100%);
}
.auth-card {
  width: 420px;
  background: #fff;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
}
.auth-logo {
  text-align: center;
  margin-bottom: 24px;
}
.auth-logo h1 {
  font-size: 22px;
  font-weight: 700;
  margin: 12px 0 4px;
  color: #303133;
}
.auth-logo p {
  color: #909399;
  font-size: 14px;
}
.auth-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
}
.tab-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
}
.wechat-label {
  color: #07C160;
}
.email-switch {
  text-align: center;
  margin-top: 12px;
  color: #606266;
  font-size: 13px;
}
.enterprise-links {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-top: 20px;
  color: #909399;
  font-size: 13px;
  border-top: 1px solid #f0f2f5;
  padding-top: 16px;
}
</style>
