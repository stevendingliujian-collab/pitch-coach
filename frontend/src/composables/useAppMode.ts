import { computed } from 'vue'
import { useRoute } from 'vue-router'

/** Routes where chrome (navbar + sidebar) should be hidden */
const CHROME_HIDDEN_PATHS = ['/auth', '/login', '/register']

export function useAppMode() {
  const route = useRoute()
  const isEmbedded = computed(() => route.query.mode === 'embedded' || route.path.startsWith('/embed'))
  const isAuthPage = computed(() => CHROME_HIDDEN_PATHS.includes(route.path))

  const showChrome = computed(() => !isEmbedded.value && !isAuthPage.value)

  return {
    isEmbedded,
    showNavbar: showChrome,
    showSidebar: showChrome,
    containerClass: computed(() => isEmbedded.value ? 'embedded-container' : 'standalone-container'),
  }
}
