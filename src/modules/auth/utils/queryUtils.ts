// modules/auth/utils/queryUtils.ts
import { isAuthError, isClientError } from '@/shared/utils/errorGuards'

/**
 * Query keys for consistent cache management
 */
export const authQueryKeys = {
  all: ['auth'] as const,
  user: () => [...authQueryKeys.all, 'user'] as const,
  me: () => [...authQueryKeys.all, 'me'] as const,
} as const

// Re-export error guards for backward compatibility
export { isAuthError, isClientError }

/**
 * Create retry function for auth queries with configurable attempts
 */
export function createAuthRetryFunction(maxAttempts = 2) {
  return (failureCount: number, error: unknown) => {
    // Don't retry on authentication errors
    if (isAuthError(error)) {
      return false
    }
    // Retry other errors up to maxAttempts times
    return failureCount < maxAttempts
  }
}

/**
 * Create retry function for auth mutations with configurable attempts
 */
export function createAuthMutationRetryFunction(maxAttempts = 2) {
  return (failureCount: number, error: unknown) => {
    // Don't retry on client errors (4xx)
    if (isClientError(error)) {
      return false
    }
    // Retry server errors up to maxAttempts times
    return failureCount < maxAttempts
  }
}

/**
 * Default retry function for auth queries (2 attempts)
 */
export const authRetryFunction = createAuthRetryFunction()

/**
 * Default retry function for auth mutations (2 attempts)
 */
export const authMutationRetryFunction = createAuthMutationRetryFunction()