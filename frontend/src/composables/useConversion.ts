/**
 * useConversion — frontend composable for upgrade trigger checks + analytics
 *
 * Usage:
 *   const { checkTrigger, trackEvent } = useConversion()
 *
 *   // After AI narration reaches page 3:
 *   await checkTrigger('T1', { page: 3 })
 *
 *   // After completing a rehearsal:
 *   await checkTrigger('T2')
 *
 *   // Track a custom analytics event:
 *   await trackEvent('plan_generated', { task_id: 42 })
 *
 * The composable calls the /api/v1/conversion backend and, when should_show=true,
 * fires the UpgradeBanner via useUpgradeBanner().show().
 */
import { useUpgradeBanner } from '@/composables/useUpgradeBanner'
import { api } from '@/api/index'

interface TriggerResponse {
  should_show: boolean
  trigger_id: string
  label: string
  message: string
}

export function useConversion() {
  const { show: showBanner } = useUpgradeBanner()

  /**
   * Check whether an upgrade trigger should be shown.
   * If yes, fires the UpgradeBanner automatically.
   * Errors are swallowed — conversion checks must never break the main flow.
   */
  async function checkTrigger(
    triggerId: string,
    meta?: Record<string, unknown>,
  ): Promise<boolean> {
    try {
      const res = await api.get<TriggerResponse>(`/conversion/trigger/${triggerId}`)
      const data = res.data
      if (data.should_show) {
        showBanner({
          feature: triggerId,
          used: 0,
          limit: 0,
          label: data.label,
          message: data.message,
          trigger_id: triggerId,
        })
        return true
      }
    } catch {
      // Silently ignore — conversion must not interfere with core UX
    }
    return false
  }

  /**
   * Record that the user dismissed an upgrade banner for a trigger.
   */
  async function recordDismissed(triggerId: string): Promise<void> {
    try {
      await api.post(`/conversion/trigger/${triggerId}/dismissed`)
    } catch {
      // ignore
    }
  }

  /**
   * Record that the user clicked "Upgrade" from a trigger banner.
   */
  async function recordConverted(triggerId: string): Promise<void> {
    try {
      await api.post(`/conversion/trigger/${triggerId}/converted`)
    } catch {
      // ignore
    }
  }

  /**
   * Fire-and-forget analytics event.
   * Core events: user_registered, ppt_uploaded, plan_generated,
   *              rehearsal_completed, daily_practice_done, upgrade_clicked
   */
  async function trackEvent(
    eventName: string,
    properties?: Record<string, unknown>,
  ): Promise<void> {
    try {
      await api.post('/conversion/events', { event_name: eventName, properties })
    } catch {
      // ignore
    }
  }

  return { checkTrigger, recordDismissed, recordConverted, trackEvent }
}
