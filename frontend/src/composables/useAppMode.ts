import { computed } from 'vue'
import { useRoute } from 'vue-router'

export function useAppMode() {
  const route = useRoute()
  const isEmbedded = computed(() => route.query.mode === 'embedded' || route.path.startsWith('/embed'))

  return {
    isEmbedded,
    showNavbar: computed(() => !isEmbedded.value),
    showSidebar: computed(() => !isEmbedded.value),
    containerClass: computed(() => isEmbedded.value ? 'embedded-container' : 'standalone-container'),
  }
}
