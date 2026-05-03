<template>
  <div class="wechat-qr">
    <div v-if="state === 'loading'" class="qr-placeholder">
      <el-icon class="spin" size="32" color="#07C160"><Loading /></el-icon>
      <p>正在生成二维码…</p>
    </div>

    <div v-else-if="state === 'ready' || state === 'pending'" class="qr-wrapper">
      <img :src="qrcodeUrl" alt="微信扫码" class="qr-img" />
      <p class="qr-hint">
        <el-icon color="#07C160"><ChatDotRound /></el-icon>
        打开微信扫一扫
      </p>
    </div>

    <div v-else-if="state === 'scanned'" class="qr-scanned">
      <el-icon size="48" color="#07C160"><SuccessFilled /></el-icon>
      <p>扫码成功，请在手机上确认</p>
    </div>

    <div v-else-if="state === 'confirmed'" class="qr-confirmed">
      <el-icon size="48" color="#409eff"><SuccessFilled /></el-icon>
      <p>登录成功，跳转中…</p>
    </div>

    <div v-else-if="state === 'expired'" class="qr-expired">
      <p>二维码已过期</p>
      <el-button type="primary" link @click="init">点击刷新</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { authApi, type TokenResponse } from '@/api/auth'

const emit = defineEmits<{
  (e: 'success', token: TokenResponse): void
}>()

type State = 'loading' | 'ready' | 'pending' | 'scanned' | 'confirmed' | 'expired'

const state = ref<State>('loading')
const qrcodeUrl = ref('')
const sessionKey = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null

async function init() {
  state.value = 'loading'
  if (pollTimer) clearInterval(pollTimer)
  try {
    const res = await authApi.wechatQrcode()
    qrcodeUrl.value = res.data.qrcode_url
    sessionKey.value = res.data.session_key
    state.value = 'pending'
    startPolling()
  } catch {
    state.value = 'expired'
  }
}

function startPolling() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    if (!sessionKey.value) return
    try {
      const res = await authApi.wechatQrcodeStatus(sessionKey.value)
      const s = res.data.status
      if (s === 'scanned') {
        state.value = 'scanned'
      } else if (s === 'confirmed' && res.data.token_response) {
        state.value = 'confirmed'
        clearInterval(pollTimer!)
        emit('success', res.data.token_response)
      } else if (s === 'expired') {
        state.value = 'expired'
        clearInterval(pollTimer!)
      }
    } catch {
      // ignore transient errors
    }
  }, 2000)
}

onMounted(init)
onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })
</script>

<style scoped>
.wechat-qr {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 0;
}
.qr-placeholder, .qr-scanned, .qr-confirmed, .qr-expired {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #606266;
  font-size: 14px;
  min-height: 200px;
  justify-content: center;
}
.qr-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.qr-img {
  width: 200px;
  height: 200px;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}
.qr-hint {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #07C160;
  font-size: 14px;
}
.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin { from { transform: rotate(0deg) } to { transform: rotate(360deg) } }
</style>
