/* eslint-disable @typescript-eslint/no-explicit-any */
import { isAxiosError } from 'axios'
import { bootstrapAuth } from '@/modules/auth/composables/useAuthBootstrap'
import { AuthRouteNames } from '@/modules/auth/config/routes'
import { authService } from '@/modules/auth/services/authService'
import { useAuthStore } from '@/modules/auth/store/useAuthStore'
import { config } from '@/shared/config/config'
// modules/auth/guards/authGuard.ts
import type { NavigationGuardNext, RouteLocationNormalized, Router } from 'vue-router'

/**
 * Auth guard that handles:
 * - Protected routes (requiresAuth meta)
 * - Guest-only routes (requiresGuest meta)
 * - Auto-refresh user data when JWT exists but user data is missing
 * - Auto-logout on 401 errors
 *
 * Note: Only active when backend is enabled (VITE_ENABLE_BACKEND=true)
 */
export async function authGuard(
  to: RouteLocationNormalized,
  _from: RouteLocationNormalized,
  next: NavigationGuardNext,
): Promise<void> {
  // Skip all auth checks if backend is disabled
  if (!config.backend.enabled) {
    next()
    return
  }

  // Restore the session from the HttpOnly refresh cookie before evaluating
  // auth requirements. Memoized — a no-op after the first navigation.
  await bootstrapAuth()

  const requiresAuth = to.matched.some(r => r.meta.requiresAuth)
  const requiresGuest = to.matched.some(r => r.meta.requiresGuest)
  const authStore = useAuthStore()
  const TWO_FACTOR_VERIFY_ROUTE = '/auth/2fa/verify'

  // Skip auth checks for 2FA verify route - twoFactorGuard handles it
  if (to.path === TWO_FACTOR_VERIFY_ROUTE) {
    next()
    return
  }

  const hasToken: boolean = !!authStore.token
  const hasUser: boolean = !!authStore.user
  let isAuthenticated: boolean = hasToken && hasUser

  // Try to refetch user data if we have token but no user data
  // BUT: Skip this if user is in 2FA flow (has twoFactorToken but no token)
  // Fetch user for all routes when token exists to restore session on page load
  const isIn2FAFlow = !!authStore.twoFactorToken && !hasToken
  if (hasToken && !hasUser && !isIn2FAFlow) {
    try {
      // Add timeout to prevent hanging forever
      const timeoutPromise = new Promise<never>((_, reject) => {
        setTimeout(() => reject(new Error('User fetch timeout')), 5000)
      })

      const user = await Promise.race([
        authService.getCurrentUser(),
        timeoutPromise
      ])

      // Map avatarUrl from backend to avatar in frontend
      authStore.setUser({
        ...user,
        avatarUrl: (user as any).avatarUrl || user.avatarUrl,
      })
      isAuthenticated = true // User is now authenticated after successful fetch
    } catch (error) {
      if (isAxiosError(error)) {
        // Handle email verification requirement
        if (error.response?.status === 403 && error.response.data?.detail === 'Email verification required') {
          next({ name: AuthRouteNames.verifyEmail, query: { email: authStore.user?.email ?? '' } })
          return
        }

        // Handle 2FA verification requirement
        // Backend returns 401 with detail about 2FA when user has 2FA enabled but token doesn't have tfaVerified=true
        if (error.response?.status === 401) {
          const detail = error.response.data?.detail ?? ''
          if (detail.includes('2FA verification required') || detail.includes('two-factor authentication')) {
            // User has 2FA enabled but token doesn't have tfaVerified=true
            // This should not happen if 2FA flow is working correctly
            // But if it does, clear the invalid token
            console.warn('[authGuard] 2FA verification required but no 2FA token found, clearing token')
            authStore.clearToken()
            authStore.clearUser()
            next({ name: AuthRouteNames.login, query: { redirectTo: to.fullPath } })
            return
          }
        }
      }

      console.warn('[authGuard] Failed to fetch user data, logging out', error)
      authStore.logout()
      isAuthenticated = false
    }
  }

  // Check auth requirements and redirect if needed
  if (requiresAuth && !isAuthenticated) {
    next({ name: AuthRouteNames.login, query: { redirectTo: to.fullPath } }); return
  }

  if (requiresGuest && isAuthenticated) {
    next({ name: 'home' }); return
  }

  // Allow navigation
  next()
}

/**
 * Helper to install auth guard on router
 * Usage: protectRoutes(router)
 */
export function protectRoutes(router: Router): void {
  router.beforeEach(authGuard)
}
