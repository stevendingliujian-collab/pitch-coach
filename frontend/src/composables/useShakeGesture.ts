/**
 * useShakeGesture — Mobile shake detection composable
 *
 * Detects a "shake" gesture using the DeviceMotion API.
 * On iOS 13+, permission must be explicitly requested by the user via a button click.
 *
 * Usage:
 *   const { isSupported, isListening, startListening, stopListening } = useShakeGesture(onShake)
 *
 *   function onShake() {
 *     startRecording()
 *   }
 */
import { ref, onUnmounted } from 'vue'

/** Minimum acceleration (m/s²) to count as a shake */
const SHAKE_THRESHOLD = 15
/** Minimum ms between two shake events */
const SHAKE_DEBOUNCE_MS = 800

export function useShakeGesture(onShake: () => void) {
  const isSupported = ref(
    typeof window !== 'undefined' && 'DeviceMotionEvent' in window
  )
  const isListening = ref(false)
  const needsPermission = ref(
    // iOS 13+ requires explicit permission
    typeof (DeviceMotionEvent as any).requestPermission === 'function'
  )

  let lastShakeAt = 0
  let lastX = 0
  let lastY = 0
  let lastZ = 0
  let initialized = false

  function handleMotion(event: DeviceMotionEvent) {
    const acc = event.accelerationIncludingGravity
    if (!acc) return

    const { x = 0, y = 0, z = 0 } = acc
    if (!initialized) {
      lastX = x ?? 0; lastY = y ?? 0; lastZ = z ?? 0
      initialized = true
      return
    }

    const deltaX = Math.abs((x ?? 0) - lastX)
    const deltaY = Math.abs((y ?? 0) - lastY)
    const deltaZ = Math.abs((z ?? 0) - lastZ)
    const acceleration = (deltaX + deltaY + deltaZ) / 3

    lastX = x ?? 0; lastY = y ?? 0; lastZ = z ?? 0

    if (acceleration > SHAKE_THRESHOLD) {
      const now = Date.now()
      if (now - lastShakeAt > SHAKE_DEBOUNCE_MS) {
        lastShakeAt = now
        onShake()
      }
    }
  }

  function startListening() {
    if (!isSupported.value || isListening.value) return
    window.addEventListener('devicemotion', handleMotion)
    isListening.value = true
    initialized = false
  }

  function stopListening() {
    if (!isListening.value) return
    window.removeEventListener('devicemotion', handleMotion)
    isListening.value = false
  }

  /**
   * On iOS 13+, must be called from a user gesture (button click).
   * Requests permission, then starts listening.
   */
  async function requestAndStart(): Promise<boolean> {
    if (!isSupported.value) return false

    if (needsPermission.value) {
      try {
        const permission = await (DeviceMotionEvent as any).requestPermission()
        if (permission !== 'granted') return false
        needsPermission.value = false
      } catch {
        return false
      }
    }

    startListening()
    return true
  }

  onUnmounted(stopListening)

  return {
    isSupported,
    isListening,
    needsPermission,
    startListening,
    stopListening,
    requestAndStart,
  }
}
