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

  function connect() {
    if (!auth.tenantId) return
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
    ws = new WebSocket(`${protocol}://${location.host}/ws/${auth.tenantId}`)
    ws.onmessage = (e) => {
      try { onMessage(JSON.parse(e.data)) } catch { /* ignore */ }
    }
    ws.onclose = () => {
      setTimeout(connect, 3000) // auto-reconnect
    }
  }

  connect()

  onUnmounted(() => {
    ws?.close()
  })

  return { ws }
}
