// modules/auth/composables/useAuthBootstrap.ts
import { authService } from '@/modules/auth/services/authService'
import { useAuthStore } from '@/modules/auth/store/useAuthStore'
import { config } from '@/shared/config/config'
import { ensureCsrfToken } from '@/shared/services/csrf'

/**
 * Silently restores a session on app boot from the HttpOnly refresh cookie.
 *
 * The access token now lives in memory only (not localStorage), so a hard
 * reload starts with no token even though the refresh cookie may still be
 * valid. Memoized to a single in-flight/resolved promise: main.ts fires it
 * eagerly to start the network round-trip as early as possible, and
 * authGuard awaits the same promise before evaluating `requiresAuth` on the
 * first navigation — awaiting after `app.mount()` isn't enough, since Vue
 * Router's initial navigation (and its guards) starts as soon as
 * `app.use(router)` runs, independent of mount. Never throws — a missing or
 * expired cookie just leaves the user logged out, same as no session.
 */
let bootstrapPromise: Promise<void> | null = null

async function performBootstrap(): Promise<void> {
  if (!config.backend.enabled) {
    return
  }

  // CSRF cookie must exist before POST /auth/refresh (double-submit).
  try {
    await ensureCsrfToken()
  } catch {
    // Proceed — refresh will fail closed if CSRF cannot be obtained.
  }

  const authStore = useAuthStore()
  try {
    const response = await authService.refreshAccessToken()
    authStore.setToken(response.accessToken)
  } catch {
    // No valid session to restore — stay logged out.
  }
}

export function bootstrapAuth(): Promise<void> {
  if (!bootstrapPromise) {
    bootstrapPromise = performBootstrap()
  }
  return bootstrapPromise
}
