 
import { AuthRouteNames } from '@/modules/auth/config/routes'
import { usePermissions } from '@/shared/composables/usePermissions'
import { config } from '@/shared/config/config'
import type { NavigationGuardNext, RouteLocationNormalized, Router } from 'vue-router'

/**
 * Admin guard that checks if user has admin or owner access
 * Should be called after authGuard
 */
export async function adminGuard(
  to: RouteLocationNormalized,
  _from: RouteLocationNormalized,
  next: NavigationGuardNext,
): Promise<void> {
  // Skip admin checks if backend is disabled
  if (!config.backend.enabled) {
    next()
    return
  }

  const requiresAdmin = to.matched.some(r => r.meta.requiresAdmin)
  if (!requiresAdmin) {
    next()
    return
  }

  const { canAccessAdminPanel, isAuthenticated } = usePermissions()

  // Check if user is authenticated
  if (!isAuthenticated.value) {
    next({ name: AuthRouteNames.login, query: { redirectTo: to.fullPath } })
    return
  }

  // Check if user has admin or owner access
  // authGuard runs before this and ensures user data is loaded
  if (!canAccessAdminPanel.value) {
    // Redirect to dashboard or home if not admin/owner
    next({ name: 'home' })
    return
  }

  // Allow navigation
  next()
}

/**
 * Helper to install admin guard on router
 * Usage: protectAdminRoutes(router)
 * Should be called after protectRoutes
 */
export function protectAdminRoutes(router: Router): void {
  router.beforeEach(adminGuard)
}
