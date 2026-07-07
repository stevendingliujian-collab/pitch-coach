import { ref, onUnmounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

export interface ProgressEvent {
  type: string
  entity_type: string
  entity_id: number
  progress: number
  stage: string
  message: string
}

export function useWebSocket(onMessage: (evt: ProgressEvent) => void) {
  const auth = useAuthStore()
  let ws: WebSocket | null = null
  let disposed = false

  function connect() {
    if (disposed || !auth.tenantId || !auth.token) return
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${protocol}://${location.host}/ws/${auth.tenantId}?token=${encodeURIComponent(auth.token)}`
    ws = new WebSocket(url)
    ws.onmessage = (e) => {
      try { onMessage(JSON.parse(e.data)) } catch { /* ignore */ }
    }
    ws.onclose = () => {
      if (!disposed) setTimeout(connect, 3000) // auto-reconnect
    }
  }

  connect()

  onUnmounted(() => {
    disposed = true
    ws?.close()
  })

  return { ws }
}
