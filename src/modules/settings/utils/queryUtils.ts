// modules/settings/utils/queryUtils.ts
import { isAuthError, isClientError } from '@/shared/utils/errorGuards'

export const settingsQueryKeys = {
  all: ['settings'] as const,
  me: () => [...settingsQueryKeys.all, 'me'] as const,
} as const

// Re-export error guards for backward compatibility
export { isAuthError, isClientError }

export function createSettingsRetryFunction(maxAttempts = 2) {
  return (failureCount: number, error: unknown) => {
    if (isAuthError(error)) return false
    return failureCount < maxAttempts
  }
}

export function createSettingsMutationRetryFunction(maxAttempts = 2) {
  return (failureCount: number, error: unknown) => {
    if (isClientError(error)) return false
    return failureCount < maxAttempts
  }
}

export const settingsRetryFunction = createSettingsRetryFunction()
export const settingsMutationRetryFunction = createSettingsMutationRetryFunction()


