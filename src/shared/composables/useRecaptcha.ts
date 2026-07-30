import { ref } from 'vue'
import { config } from '@/shared/config/config'
import { executeRecaptcha } from '@/shared/utils/recaptcha'

export function useRecaptcha() {
  const isReady = ref(false)
  const isExecuting = ref(false)
  const error = ref<string | null>(null)

  /**
   * Get reCAPTCHA token for action
   * 
   * Note: Tokens expire after ~2 minutes and are single-use.
   * Call this immediately before making API requests.
   */
  const getToken = async (action: string): Promise<string | null> => {
    if (!config.recaptcha.enabled) {
      return null
    }

    isExecuting.value = true
    error.value = null

    try {
      const token = await executeRecaptcha(action)
      
      if (!token) {
        error.value = 'Failed to generate reCAPTCHA token'
        console.warn(`[reCAPTCHA] Token generation failed for action: ${action}`)
        return null
      }
      
      isReady.value = true
      return token
    }
    catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get token'
      error.value = errorMessage
      console.error(`[reCAPTCHA] Error getting token for action ${action}:`, err)
      return null
    }
    finally {
      isExecuting.value = false
    }
  }

  return {
    error,
    getToken,
    isEnabled: config.recaptcha.enabled,
    isExecuting,
    isReady,
  }
}
