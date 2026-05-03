/**
 * useAbTest — A/B test variant assignment composable
 *
 * Usage:
 *   const { getVariant, recordConversion } = useAbTest()
 *   const variant = await getVariant('pricing_layout')
 *   // variant === 'control' | 'variant_b'
 *
 *   // When user converts (e.g. clicks upgrade):
 *   await recordConversion('pricing_layout')
 */
import { ref } from 'vue'
import { api } from '@/api/index'

// In-memory cache: test_name → variant
const cache: Record<string, string> = {}

export function useAbTest() {
  const loading = ref(false)

  /**
   * Fetch variant for one or more test names.
   * Results are cached in-memory for the session.
   */
  async function fetchVariants(testNames: string[]): Promise<Record<string, string>> {
    const uncached = testNames.filter(n => !(n in cache))
    if (uncached.length > 0) {
      try {
        loading.value = true
        const res = await api.get<{ assignments: Record<string, string> }>(
          '/ab-tests/assign',
          { params: { tests: uncached.join(',') } }
        )
        Object.assign(cache, res.data.assignments)
      } catch {
        // Silent — test infra failures shouldn't break the product
      } finally {
        loading.value = false
      }
    }
    const result: Record<string, string> = {}
    for (const n of testNames) {
      if (n in cache) result[n] = cache[n]
    }
    return result
  }

  /**
   * Get variant for a single test. Returns undefined if test is inactive/unknown.
   */
  async function getVariant(testName: string): Promise<string | undefined> {
    const map = await fetchVariants([testName])
    return map[testName]
  }

  /**
   * Record a conversion event for a test.
   */
  async function recordConversion(testName: string, meta?: Record<string, unknown>): Promise<void> {
    try {
      await api.post('/ab-tests/events', {
        test_name: testName,
        event_type: 'conversion',
        meta,
      })
    } catch {
      // Silent
    }
  }

  /**
   * Record an arbitrary event.
   */
  async function recordEvent(
    testName: string,
    eventType: string,
    meta?: Record<string, unknown>
  ): Promise<void> {
    try {
      await api.post('/ab-tests/events', {
        test_name: testName,
        event_type: eventType,
        meta,
      })
    } catch {
      // Silent
    }
  }

  return {
    loading,
    getVariant,
    fetchVariants,
    recordConversion,
    recordEvent,
  }
}
