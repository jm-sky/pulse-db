/**
 * Login Modal Composable
 * 
 * Global state management for login modal that appears
 * when session expires or 401 error occurs.
 * 
 * Usage:
 * - In error interceptor: `useLoginModal().open()`
 * - In App.vue: `<LoginModal />`
 */

import { ref } from 'vue'

interface LoginModalCallbacks {
  onSuccess?: () => void | Promise<void>
  onCancel?: () => void
}

// Global state (singleton pattern)
const isLoginModalOpen = ref(false)
const loginModalCallbacks = ref<LoginModalCallbacks>({})

export function useLoginModal() {
  /**
   * Open login modal
   * @param callbacks - Optional callbacks for success/cancel
   */
  const open = (callbacks?: LoginModalCallbacks) => {
    isLoginModalOpen.value = true
    loginModalCallbacks.value = callbacks ?? {}
  }
  
  /**
   * Close login modal
   */
  const close = () => {
    isLoginModalOpen.value = false
    loginModalCallbacks.value = {}
  }
  
  /**
   * Handle successful login
   */
  const handleSuccess = async () => {
    await loginModalCallbacks.value.onSuccess?.()
    close()
  }
  
  /**
   * Handle modal cancellation
   */
  const handleCancel = () => {
    loginModalCallbacks.value.onCancel?.()
    close()
  }
  
  return {
    isOpen: isLoginModalOpen,
    open,
    close,
    handleSuccess,
    handleCancel,
  }
}

