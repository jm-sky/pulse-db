/**
 * Axios error response interceptor
 *
 * Handles HTTP error responses globally:
 * - 401 Unauthorized: Try to refresh token automatically, if that fails open login modal
 * - Other errors: Pass through to be handled locally
 *
 * This provides centralized error handling with automatic token refresh
 * and allows users to re-authenticate without losing their current context.
 *
 * FIXED: Moved mutable state to Pinia store to prevent race conditions
 */

import { HttpStatusCode } from 'axios'
import { AUTH_BASE_PATH } from '@/modules/auth/config/routes'
import { authService } from '@/modules/auth/services/authService'
import { useAuthStore } from '@/modules/auth/store/useAuthStore'
import { useLoginModal } from '@/shared/composables/useLoginModal'
import { config } from '@/shared/config/config'
import { useTokenRefreshStore } from '@/shared/store/useTokenRefreshStore'
import { apiClient } from './apiClient'
import type { AxiosError, InternalAxiosRequestConfig } from 'axios'

/**
 * Handle axios response errors
 *
 * @param error - Axios error object
 * @returns Rejected promise with the error
 */
export async function errorResponseInterceptor(error: AxiosError) {
  const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

  // Only handle 401 if backend is enabled
  if (!config.backend.enabled) {
    // Pass error through for local handling
    return Promise.reject(error)
  }

  // Check if we're on an auth page or if the request is to an auth endpoint
  // Don't show login modal if user is already on login page
  const AUTH_PREFIX = `${AUTH_BASE_PATH}/`
  const PUBLIC_AUTH_ENDPOINTS = [
    '/login',
    '/register',
    '/forgot-password',
    '/reset-password',
    '/refresh',
    '/email/verify',
    '/email/resend',
    '/oauth/',
  ]
  const isOnAuthPage = typeof window !== 'undefined' && window.location.pathname.startsWith(AUTH_PREFIX)
  const requestUrl = originalRequest?.url ?? ''
  const isPublicAuthRequest = PUBLIC_AUTH_ENDPOINTS.some((endpoint) => {
    return requestUrl.includes(`${AUTH_BASE_PATH}${endpoint}`)
  })

  // For auth requests (login, register, etc.), pass the error through
  // so the form can handle it with field-level validation errors
  if (isPublicAuthRequest && error.response?.status === HttpStatusCode.Unauthorized) {
    return Promise.reject(error)
  }

  // Handle 401 Unauthorized errors
  if (
    error.response?.status === HttpStatusCode.Unauthorized &&
    originalRequest &&
    !originalRequest._retry
  ) {
    const authStore = useAuthStore()
    const refreshStore = useTokenRefreshStore()

    // The refresh token lives in an HttpOnly cookie the SPA can't inspect,
    // so we can't know upfront whether a session exists — just attempt the
    // refresh and let the backend say no.
    // If already refreshing, queue this request
    if (refreshStore.isRefreshing) {
      return new Promise((resolve, reject) => {
        refreshStore.addToQueue({ resolve, reject })
      })
        .then(() => {
          // Retry with new token (auth interceptor will add the new token automatically)
          return apiClient(originalRequest)
        })
        .catch((err) => {
          return Promise.reject(err)
        })
    }

    // Mark that we're refreshing
    originalRequest._retry = true
    refreshStore.setRefreshing(true)

    try {
      // Try to refresh the access token (cookie sent automatically via withCredentials)
      const response = await authService.refreshAccessToken()

      // Update access token in store
      authStore.setToken(response.accessToken)

      // Process queued requests (they will be retried with new token via auth interceptor)
      refreshStore.processQueue(null)

      // Retry the original request with new token (auth interceptor will add it)
      return apiClient(originalRequest)
    } catch (refreshError) {
      // Refresh failed - clear tokens, process queue with error, and show login modal
      refreshStore.processQueue(refreshError as Error)
      authStore.clearToken()
      authStore.clearUser()

      // Only open login modal if not on auth page and not an auth request
      if (!isOnAuthPage && !isPublicAuthRequest) {
        const loginModal = useLoginModal()
        loginModal.open({
          onSuccess: async () => {
            try {
              // After successful login, retry the original request
              // Auth interceptor will add the new token automatically
              originalRequest._retry = false // Reset retry flag for new attempt
              return await apiClient(originalRequest)
            } catch (retryError) {
              console.error('Failed to retry request after re-authentication', retryError)
              throw retryError
            }
          },
        })
      }

      return Promise.reject(refreshError)
    } finally {
      refreshStore.setRefreshing(false)
    }
  }

  // Pass error through for local handling
  return Promise.reject(error)
}
