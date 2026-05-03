<template>
  <div class="phone-verification">
    <!-- Phone input -->
    <el-form-item prop="phone">
      <el-input
        v-model="phone"
        placeholder="请输入手机号"
        size="large"
        maxlength="11"
        @keyup.enter="codeInputRef?.focus()"
      >
        <template #prepend>+86</template>
      </el-input>
    </el-form-item>

    <!-- Code input + send button -->
    <el-form-item prop="code">
      <el-input
        ref="codeInputRef"
        v-model="code"
        placeholder="6 位验证码"
        size="large"
        maxlength="6"
        @keyup.enter="emit('submit', phone, code)"
      >
        <template #append>
          <el-button
            :disabled="!canSend || cooldown > 0"
            :loading="sending"
            @click="sendCode"
          >
            {{ cooldown > 0 ? `${cooldown}s 后重发` : '获取验证码' }}
          </el-button>
        </template>
      </el-input>
    </el-form-item>

    <el-button
      type="primary"
      size="large"
      :loading="props.loading"
      :disabled="!canSubmit"
      style="width:100%;margin-top:4px"
      @click="emit('submit', phone, code)"
    >
      {{ props.submitText }}
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { authApi } from '@/api/auth'

const props = withDefaults(defineProps<{
  loading?: boolean
  submitText?: string
}>(), {
  loading: false,
  submitText: '登录 / 注册',
})

const emit = defineEmits<{
  (e: 'submit', phone: string, code: string): void
}>()

const phone = ref('')
const code = ref('')
const sending = ref(false)
const cooldown = ref(0)
const codeInputRef = ref()
let cooldownTimer: ReturnType<typeof setInterval> | null = null

const canSend = computed(() => /^1[3-9]\d{9}$/.test(phone.value))
const canSubmit = computed(() => canSend.value && code.value.length === 6)

async function sendCode() {
  if (!canSend.value || cooldown.value > 0) return
  sending.value = true
  try {
    await authApi.smsSend(phone.value)
    ElMessage.success('验证码已发送')
    cooldown.value = 60
    cooldownTimer = setInterval(() => {
      cooldown.value--
      if (cooldown.value <= 0) {
        clearInterval(cooldownTimer!)
        cooldownTimer = null
      }
    }, 1000)
    codeInputRef.value?.focus()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '发送失败，请稍后重试')
  } finally {
    sending.value = false
  }
}
</script>

<style scoped>
.phone-verification {
  width: 100%;
}
</style>
