/**
 * Token Refresh Store
 *
 * Manages token refresh state and queued requests in a reactive way.
 * This replaces global mutable state in error.interceptor.ts to prevent race conditions.
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface QueuedRequest {
  resolve: (value?: unknown) => void
  reject: (reason?: unknown) => void
}

export const useTokenRefreshStore = defineStore('tokenRefresh', () => {
  // State
  const isRefreshing = ref(false)
  const failedQueue = ref<QueuedRequest[]>([])

  // Actions
  function setRefreshing(value: boolean) {
    isRefreshing.value = value
  }

  function addToQueue(request: QueuedRequest) {
    failedQueue.value.push(request)
  }

  function processQueue(error: Error | null) {
    failedQueue.value.forEach((promise) => {
      if (error) {
        promise.reject(error)
      } else {
        promise.resolve()
      }
    })
    clearQueue()
  }

  function clearQueue() {
    failedQueue.value = []
  }

  function reset() {
    isRefreshing.value = false
    failedQueue.value = []
  }

  return {
    // State
    isRefreshing,
    failedQueue,

    // Actions
    setRefreshing,
    addToQueue,
    processQueue,
    clearQueue,
    reset,
  }
})
