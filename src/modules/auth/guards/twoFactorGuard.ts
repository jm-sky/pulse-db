import { AuthRoutePaths } from '@/modules/auth/config/routes'
// modules/auth/guards/twoFactorGuard.ts
import { requiresTwoFactorVerification } from '@/modules/auth/lib/jwtDecoder'
import { useAuthStore } from '@/modules/auth/store/useAuthStore'
import type { NavigationGuardNext, RouteLocationNormalized, Router } from 'vue-router'

const TWO_FACTOR_VERIFY_ROUTE = '/auth/2fa/verify'
const TWO_FACTOR_SETUP_ROUTE = '/auth/2fa/setup'

/**
 * 2FA guard that checks for 2FA verification status
 * - If user has 2FA token but no access token, redirect to verify page
 * - If access token has tfaPending=true and tfaVerified=false, redirect to verify page
 * - If accessing verify page without 2FA token/pending status, redirect to dashboard
 * - Allows access to setup page regardless of 2FA status
 */
export function twoFactorGuard(
  to: RouteLocationNormalized,
  _from: RouteLocationNormalized,
  next: NavigationGuardNext,
): void {
  const authStore = useAuthStore()
  const token = authStore.token
  const twoFactorToken = authStore.twoFactorToken
  const isTwoFactorPending = authStore.isTwoFactorPending

  // Allow access to 2FA setup page
  if (to.path === TWO_FACTOR_SETUP_ROUTE) {
    next()
    return
  }

  // Check if user is in 2FA flow (has 2FA token but no access token)
  if (isTwoFactorPending || twoFactorToken) {
    // Allow access to verify page
    if (to.path === TWO_FACTOR_VERIFY_ROUTE) {
      next()
      return
    }

    // Redirect to verify page for any other route
    next({
      path: TWO_FACTOR_VERIFY_ROUTE,
      query: { redirectTo: to.fullPath },
    })
    return
  }

  // If user has access token, check if 2FA verification is required in the token
  if (token) {
    const needsVerification = requiresTwoFactorVerification(token)

    // If 2FA verification is required in the token
    if (needsVerification) {
      // Allow access to verify page
      if (to.path === TWO_FACTOR_VERIFY_ROUTE) {
        next()
        return
      }

      // Redirect to verify page for any other route
      next({
        path: TWO_FACTOR_VERIFY_ROUTE,
        query: { redirectTo: to.fullPath },
      })
      return
    }

    // If accessing verify page but 2FA is already verified, redirect to dashboard
    if (to.path === TWO_FACTOR_VERIFY_ROUTE) {
      next({ path: AuthRoutePaths.dashboard })
      return
    }
  }

  // Allow navigation
  next()
}

/**
 * Helper to install 2FA guard on router
 * Should be called after authGuard
 * Usage: protectRoutesWithTwoFactor(router)
 */
export function protectRoutesWithTwoFactor(router: Router): void {
  router.beforeEach(twoFactorGuard)
}
