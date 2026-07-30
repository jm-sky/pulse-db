// shared/composables/useBackend.ts
import { computed } from 'vue'
import { useAuthStore } from '@/modules/auth/store/useAuthStore'
import { config } from '@/shared/config/config'

/**
 * Composable to check if backend is enabled and if user is authenticated
 * 
 * @example
 * ```ts
 * const { isBackendEnabled, backendUrl, isAuthenticated, shouldUseAPI } = useBackend()
 * 
 * if (shouldUseAPI.value) {
 *   // Use backend API (backend enabled AND user authenticated)
 *   await apiClient.post('/auth/login', credentials)
 * } else {
 *   // Use localStorage (offline mode or not authenticated)
 *   localStorage.setItem('user', JSON.stringify(user))
 * }
 * ```
 */
export function useBackend() {
  const isBackendEnabled = computed(() => config.backend.enabled)
  const backendUrl = computed(() => config.backend.baseUrl)
  
  /**
   * Check if user has authentication token
   * Simple check - just verifies the in-memory access token exists
   */
  const isAuthenticated = computed(() => {
    return !!useAuthStore().token
  })
  
  /**
   * Should use API: backend enabled AND user authenticated
   * This is the main check for hybrid services (localStorage vs API)
   */
  const shouldUseAPI = computed(() => {
    return isBackendEnabled.value && isAuthenticated.value
  })

  return {
    isBackendEnabled,
    backendUrl,
    isAuthenticated,
    shouldUseAPI,
  }
}
