import { ref, readonly } from 'vue'
import type { PageTiming } from '@/api/rehearsal'

type RecordingState = 'idle' | 'recording' | 'paused' | 'stopped'

export function useRehearsalRecorder() {
  const state = ref<RecordingState>('idle')
  const durationSec = ref(0)
  const audioBlob = ref<Blob | null>(null)
  const pageTimings = ref<PageTiming[]>([])

  let mediaRecorder: MediaRecorder | null = null
  let chunks: Blob[] = []
  let startTime = 0
  let pausedAt = 0
  let pausedDuration = 0
  let timerHandle: ReturnType<typeof setInterval> | null = null
  let currentPage = 1
  let pageStartTime = 0

  const elapsed = () => {
    if (startTime === 0) return 0
    return (Date.now() - startTime - pausedDuration) / 1000
  }

  async function start(pageNumber = 1) {
    if (state.value !== 'idle') return

    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        sampleRate: 16000,
        echoCancellation: true,
        noiseSuppression: true,
      },
    })

    // Prefer webm/opus; fallback to whatever browser supports
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : ''

    mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
    chunks = []
    mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data) }

    mediaRecorder.start(500) // collect chunks every 500ms
    startTime = Date.now()
    pausedDuration = 0
    currentPage = pageNumber
    pageStartTime = 0

    state.value = 'recording'
    timerHandle = setInterval(() => { durationSec.value = Math.round(elapsed()) }, 500)
  }

  function turnPage(nextPage: number) {
    if (state.value !== 'recording') return
    const now = elapsed()
    pageTimings.value.push({
      page_number: currentPage,
      start_sec: pageStartTime,
      end_sec: now,
    })
    currentPage = nextPage
    pageStartTime = now
  }

  function pause() {
    if (state.value !== 'recording') return
    mediaRecorder?.pause()
    pausedAt = Date.now()
    state.value = 'paused'
    if (timerHandle) clearInterval(timerHandle)
  }

  function resume() {
    if (state.value !== 'paused') return
    mediaRecorder?.resume()
    pausedDuration += Date.now() - pausedAt
    state.value = 'recording'
    timerHandle = setInterval(() => { durationSec.value = Math.round(elapsed()) }, 500)
  }

  async function stop(): Promise<Blob> {
    return new Promise((resolve) => {
      if (!mediaRecorder || state.value === 'idle') {
        resolve(new Blob())
        return
      }

      // Record the final page timing
      const now = elapsed()
      pageTimings.value.push({
        page_number: currentPage,
        start_sec: pageStartTime,
        end_sec: now,
      })

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: mediaRecorder!.mimeType || 'audio/webm' })
        audioBlob.value = blob
        durationSec.value = Math.round(now)

        // Stop microphone tracks
        mediaRecorder!.stream.getTracks().forEach((t) => t.stop())
        state.value = 'stopped'
        if (timerHandle) clearInterval(timerHandle)
        resolve(blob)
      }

      mediaRecorder.stop()
    })
  }

  function reset() {
    if (timerHandle) clearInterval(timerHandle)
    mediaRecorder?.stream.getTracks().forEach((t) => t.stop())
    mediaRecorder = null
    chunks = []
    startTime = 0
    pausedAt = 0
    pausedDuration = 0
    currentPage = 1
    pageStartTime = 0
    state.value = 'idle'
    durationSec.value = 0
    audioBlob.value = null
    pageTimings.value = []
  }

  return {
    state: readonly(state),
    durationSec: readonly(durationSec),
    audioBlob: readonly(audioBlob),
    pageTimings: readonly(pageTimings),
    start,
    turnPage,
    pause,
    resume,
    stop,
    reset,
  }
}
