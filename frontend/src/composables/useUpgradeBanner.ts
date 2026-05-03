/**
 * useUpgradeBanner — global singleton composable
 *
 * Usage:
 *   const { show } = useUpgradeBanner()
 *   show({ feature: 'ppt_uploads', used: 3, limit: 3, message: '...' })
 *
 * The UpgradeBanner.vue component reads this shared state via the same composable.
 * The axios interceptor in api/index.ts calls show() on 402 responses.
 */
import { ref, readonly } from 'vue'
import { ElMessage } from 'element-plus'

interface BannerPayload {
  feature: string
  used: number
  limit: number
  label?: string
  message?: string
  trigger_id?: string
}

// Module-level singletons so all callers share the same state
const _visible = ref(false)
const _title = ref('')
const _message = ref('')
const _usage = ref<{ used: number; limit: number; pct: number } | null>(null)
const _triggerId = ref<string | null>(null)
let _dismissTimer: ReturnType<typeof setTimeout> | null = null

export function useUpgradeBanner() {
  function show(payload: BannerPayload) {
    const label = payload.label || payload.feature
    // For conversion triggers (T1-T9), use their message directly; for quota hits use "已达X上限"
    const isConversionTrigger = payload.trigger_id && /^T\d+$/.test(payload.trigger_id)
    _title.value = isConversionTrigger
      ? (payload.message || `升级专业版，享受更多功能。`)
      : `已达${label}上限`
    _message.value = isConversionTrigger
      ? ''
      : (payload.message || `升级专业版，享受无限次使用。`)
    _usage.value = payload.limit > 0
      ? {
          used: payload.used,
          limit: payload.limit,
          pct: Math.round((payload.used / payload.limit) * 100),
        }
      : null
    _triggerId.value = payload.trigger_id ?? null
    _visible.value = true

    // Auto-hide after 12s
    if (_dismissTimer) clearTimeout(_dismissTimer)
    _dismissTimer = setTimeout(() => { _visible.value = false }, 12000)
  }

  function dismiss() {
    // Record dismiss event (best-effort, fire-and-forget)
    if (_triggerId.value) {
      const tid = _triggerId.value
      import('@/api/index').then(({ api }) => {
        api.post(`/conversion/trigger/${tid}/dismissed`).catch(() => {})
      })
    }
    _visible.value = false
    _triggerId.value = null
    if (_dismissTimer) clearTimeout(_dismissTimer)
  }

  function openUpgrade() {
    // Record conversion click (best-effort)
    if (_triggerId.value) {
      const tid = _triggerId.value
      import('@/api/index').then(({ api }) => {
        api.post(`/conversion/trigger/${tid}/converted`).catch(() => {})
        api.post('/conversion/events', { event_name: 'upgrade_clicked', properties: { trigger_id: tid } }).catch(() => {})
      })
    }
    // P2: navigate to /pricing. For now show info message.
    ElMessage({
      message: '定价与订阅功能将在 P2 版本正式上线，敬请期待！',
      type: 'info',
      duration: 3000,
    })
    _visible.value = false
    _triggerId.value = null
    if (_dismissTimer) clearTimeout(_dismissTimer)
  }

  return {
    visible: readonly(_visible),
    title: readonly(_title),
    message: readonly(_message),
    usage: readonly(_usage),
    triggerId: readonly(_triggerId),
    show,
    dismiss,
    openUpgrade,
  }
}
