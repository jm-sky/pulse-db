import { useMutation, useQueryClient } from '@tanstack/vue-query'
// modules/auth/composables/useTotp.ts
import { twoFactorService } from '@/modules/auth/services/twoFactorService'
import { useAuthStore } from '@/modules/auth/store/useAuthStore'
import { twoFactorQueryKeys } from './useTwoFactor'
import type { ITwoFactorService } from '@/modules/auth/types/twoFactor.type'

/**
 * Hook for setting up TOTP
 */
export function useSetupTotp(service?: ITwoFactorService) {
  return useMutation({
    mutationFn: async () => {
      return (service ?? twoFactorService).setupTotp()
    },
    onSuccess: () => {
      // Don't invalidate status yet - only after verification
    },
  })
}

/**
 * Hook for verifying TOTP code during setup (requires setupToken)
 */
export function useVerifyTotp(service?: ITwoFactorService) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ setupToken, code }: { setupToken: string; code: string }) => {
      return (service ?? twoFactorService).verifyTotp(setupToken, code)
    },
    onSuccess: async (data) => {
      if (data.verified) {
        // Invalidate all 2FA queries to refresh status
        await queryClient.invalidateQueries({ queryKey: twoFactorQueryKeys.all })
      }
    },
  })
}

/**
 * Hook for verifying TOTP code during login
 */
export function useVerifyTotpLogin(service?: ITwoFactorService) {
  const queryClient = useQueryClient()
  const authStore = useAuthStore()

  return useMutation({
    mutationFn: async ({ code, twoFactorToken }: { code: string; twoFactorToken: string }) => {
      return (service ?? twoFactorService).verifyTotpLogin(twoFactorToken, code)
    },
    onSuccess: async (data) => {
      if (data.verified && data.accessToken) {
        // Store the access token (refresh token is an HttpOnly cookie)
        authStore.setToken(data.accessToken)
        // Clear 2FA token
        authStore.clearTwoFactorToken()
        // Invalidate all 2FA queries to refresh status
        await queryClient.invalidateQueries({ queryKey: twoFactorQueryKeys.all })
        // Don't invalidate user queries here - let the guard or component handle it after redirect
        // This prevents infinite loops during redirect
      }
    },
  })
}

/**
 * Hook for disabling TOTP
 */
export function useDisableTotp(service?: ITwoFactorService) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (password: string) => {
      return (service ?? twoFactorService).disableTotp(password)
    },
    onSuccess: async () => {
      // Invalidate all 2FA queries to refresh status
      await queryClient.invalidateQueries({ queryKey: twoFactorQueryKeys.all })
    },
  })
}
