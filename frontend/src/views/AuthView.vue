<template>
  <div class="auth-root">
    <!-- ─── Left panel: brand ─────────────────────────────────────────── -->
    <div class="auth-left">
      <div class="brand-inner">
        <!-- Logo -->
        <div class="brand-logo">
          <el-icon size="28" color="#fff"><TrendCharts /></el-icon>
          <span>OTD AI 述标教练</span>
        </div>

        <!-- Headline -->
        <div class="brand-hero">
          <h1>把金牌售前的<br>述标能力<br><em>变成公司资产</em></h1>
          <p>AI 驱动的述标训练平台，帮助销售团队<br>系统化提升投标演示水平，提高中标率</p>
        </div>

        <!-- Feature list -->
        <ul class="brand-features">
          <li>
            <span class="feat-icon">📊</span>
            <div>
              <strong>一键生成述标方案</strong>
              <small>上传 PPT，AI 按页提炼核心讲解要点</small>
            </div>
          </li>
          <li>
            <span class="feat-icon">🎤</span>
            <div>
              <strong>对练排练 · 实时评分</strong>
              <small>语速 / 填充词 / 要点覆盖率三维分析</small>
            </div>
          </li>
          <li>
            <span class="feat-icon">🔥</span>
            <div>
              <strong>每日微练习</strong>
              <small>5 分钟养成述标习惯，完全免费无限次</small>
            </div>
          </li>
        </ul>

        <!-- Tagline -->
        <div class="brand-quote">
          <span class="quote-mark">"</span>
          免费让你爱上练习，付费让你赢得投标
          <span class="quote-mark">"</span>
        </div>
      </div>

      <!-- Decorative shapes -->
      <div class="deco deco-1" />
      <div class="deco deco-2" />
      <div class="deco deco-3" />
    </div>

    <!-- ─── Right panel: auth form ────────────────────────────────────── -->
    <div class="auth-right">
      <div class="form-inner">
        <!-- Header -->
        <div class="form-header">
          <h2>欢迎使用</h2>
          <p>登录或注册，开始你的述标训练</p>
        </div>

        <!-- Tabs -->
        <el-tabs v-model="activeTab" class="auth-tabs" stretch>
          <!-- WeChat -->
          <el-tab-pane name="phone">
            <template #label>
              <span class="tab-lbl"><el-icon><Iphone /></el-icon> 手机号</span>
            </template>
            <PhoneVerification
              :loading="phoneLoading"
              submit-text="登录 / 注册"
              @submit="handlePhoneLogin"
            />
          </el-tab-pane>

          <el-tab-pane name="wechat">
            <template #label>
              <span class="tab-lbl wechat-lbl"><el-icon><ChatDotRound /></el-icon> 微信扫码</span>
            </template>
            <WechatQrCode @success="handleTokenResponse" />
          </el-tab-pane>

          <!-- Email (folded) -->
          <el-tab-pane name="email">
            <template #label>
              <span class="tab-lbl"><el-icon><Message /></el-icon> 邮箱</span>
            </template>

            <el-form
              ref="emailFormRef"
              :model="emailForm"
              :rules="emailRules"
              label-position="top"
              class="email-form"
              @submit.prevent="handleEmailAuth"
            >
              <el-form-item label="邮箱" prop="email">
                <el-input v-model="emailForm.email" type="email" placeholder="your@email.com" size="large" />
              </el-form-item>
              <el-form-item label="密码" prop="password">
                <el-input v-model="emailForm.password" type="password" placeholder="请输入密码（≥8位）" size="large" show-password />
              </el-form-item>
              <el-form-item v-if="emailMode === 'register'" label="姓名（选填）">
                <el-input v-model="emailForm.name" placeholder="您的姓名" size="large" />
              </el-form-item>
              <el-button
                type="primary"
                size="large"
                :loading="emailLoading"
                native-type="submit"
                class="submit-btn"
              >
                {{ emailMode === 'login' ? '登录' : '注册账号' }}
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

        <!-- Enterprise links -->
        <div class="enterprise-row">
          <span class="ent-label">企业用户</span>
          <el-button type="primary" link size="small" @click="showEnterpriseTip">企业微信</el-button>
          <el-divider direction="vertical" />
          <el-button type="primary" link size="small" @click="showEnterpriseTip">飞书</el-button>
          <el-divider direction="vertical" />
          <el-button type="primary" link size="small" @click="showEnterpriseTip">CRM SSO</el-button>
        </div>

        <!-- Footer -->
        <p class="form-footer">
          登录即代表同意
          <a href="#" @click.prevent>《服务协议》</a>
          与
          <a href="#" @click.prevent>《隐私政策》</a>
        </p>
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

const activeTab = ref<'phone' | 'wechat' | 'email'>('phone')
const phoneLoading = ref(false)
const emailLoading = ref(false)
const emailMode = ref<'login' | 'register'>('login')

const emailFormRef = ref<FormInstance>()
const emailForm = ref({ email: '', password: '', name: '' })
const emailRules: FormRules = {
  email: [{ required: true, type: 'email', message: '请输入有效邮箱', trigger: 'blur' }],
  password: [{ required: true, min: 8, message: '密码至少 8 位', trigger: 'blur' }],
}

function handleTokenResponse(res: TokenResponse) {
  auth.applyTokenResponse(res)
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

function showEnterpriseTip() {
  ElMessage.info('企业 IM 登录即将上线，请先使用手机号或邮箱登录')
}
</script>

<style scoped>
/* ── Root layout ─────────────────────────────────────────────────────── */
.auth-root {
  min-height: 100vh;
  display: flex;
}

/* ── Left panel ──────────────────────────────────────────────────────── */
.auth-left {
  position: relative;
  flex: 0 0 52%;
  background: linear-gradient(145deg, #0f1b35 0%, #0d2b5e 45%, #0a3d7a 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  padding: 48px;
}

.brand-inner {
  position: relative;
  z-index: 1;
  max-width: 440px;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 36px;
}

/* Logo */
.brand-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  opacity: 0.92;
}

/* Headline */
.brand-hero h1 {
  font-size: 42px;
  font-weight: 800;
  line-height: 1.2;
  color: #fff;
  margin-bottom: 16px;
  letter-spacing: -0.5px;
}
.brand-hero h1 em {
  font-style: normal;
  background: linear-gradient(90deg, #60c8ff, #a78bfa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.brand-hero p {
  font-size: 15px;
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.65);
}

/* Features */
.brand-features {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.brand-features li {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}
.feat-icon {
  font-size: 22px;
  line-height: 1;
  flex-shrink: 0;
  margin-top: 2px;
}
.brand-features strong {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.92);
  margin-bottom: 2px;
}
.brand-features small {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  line-height: 1.5;
}

/* Quote */
.brand-quote {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.45);
  font-style: italic;
  letter-spacing: 0.3px;
}
.quote-mark {
  font-size: 20px;
  color: rgba(96, 200, 255, 0.6);
  font-style: normal;
  vertical-align: -2px;
  margin: 0 2px;
}

/* Decorative blobs */
.deco {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  pointer-events: none;
}
.deco-1 {
  width: 360px; height: 360px;
  background: rgba(96, 200, 255, 0.12);
  top: -80px; right: -80px;
}
.deco-2 {
  width: 280px; height: 280px;
  background: rgba(167, 139, 250, 0.1);
  bottom: 40px; left: -60px;
}
.deco-3 {
  width: 200px; height: 200px;
  background: rgba(59, 130, 246, 0.15);
  top: 50%; left: 55%;
  transform: translate(-50%, -50%);
}

/* ── Right panel ─────────────────────────────────────────────────────── */
.auth-right {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8fafc;
  padding: 48px 32px;
}

.form-inner {
  width: 100%;
  max-width: 400px;
  display: flex;
  flex-direction: column;
  gap: 0;
}

/* Header */
.form-header {
  margin-bottom: 28px;
}
.form-header h2 {
  font-size: 26px;
  font-weight: 700;
  color: #111827;
  margin-bottom: 6px;
}
.form-header p {
  font-size: 14px;
  color: #6b7280;
}

/* Tabs */
.auth-tabs :deep(.el-tabs__header) {
  margin-bottom: 20px;
}
.auth-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
  background: #e5e7eb;
}
.auth-tabs :deep(.el-tabs__item) {
  font-size: 13px;
  padding: 0 12px;
}
.tab-lbl {
  display: flex;
  align-items: center;
  gap: 5px;
}
.wechat-lbl { color: #07C160; }
.auth-tabs :deep(.el-tabs__item.is-active) .wechat-lbl { color: #07C160; }

/* Submit button */
.submit-btn {
  width: 100%;
  margin-top: 4px;
  height: 44px;
  font-size: 15px;
  font-weight: 600;
}

/* Email form */
.email-form {
  margin-top: 4px;
}
.email-switch {
  text-align: center;
  margin-top: 12px;
  font-size: 13px;
  color: #6b7280;
}

/* Enterprise row */
.enterprise-row {
  display: flex;
  align-items: center;
  gap: 2px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #e5e7eb;
}
.ent-label {
  font-size: 12px;
  color: #9ca3af;
  margin-right: 4px;
}

/* Footer */
.form-footer {
  text-align: center;
  margin-top: 16px;
  font-size: 12px;
  color: #9ca3af;
}
.form-footer a {
  color: #6b7280;
  text-decoration: none;
}
.form-footer a:hover { text-decoration: underline; }

/* ── Responsive ──────────────────────────────────────────────────────── */
@media (max-width: 768px) {
  .auth-root { flex-direction: column; }
  .auth-left {
    flex: none;
    padding: 32px 24px 28px;
    min-height: auto;
  }
  .brand-hero h1 { font-size: 28px; }
  .brand-features { display: none; }
  .brand-quote { display: none; }
  .auth-right { padding: 32px 20px; }
}
</style>
