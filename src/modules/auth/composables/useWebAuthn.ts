import { startAuthentication, startRegistration } from '@simplewebauthn/browser'
import { useMutation, useQueryClient } from '@tanstack/vue-query'
// modules/auth/composables/useWebAuthn.ts
import { twoFactorService } from '@/modules/auth/services/twoFactorService'
import { useAuthStore } from '@/modules/auth/store/useAuthStore'
import { twoFactorQueryKeys } from './useTwoFactor'
import type {
  ITwoFactorService,
  WebAuthnRegisterRequest,
} from '@/modules/auth/types/twoFactor.type'


/**
 * Hook for registering a new passkey
 */
export function useRegisterPasskey(service?: ITwoFactorService) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (request: WebAuthnRegisterRequest) => {
      const svc = service ?? twoFactorService

      // Step 1: Get registration options from backend
      const registerResponse = await svc.registerPasskey(request)

      // Step 2: Start WebAuthn registration ceremony
      const credential = await startRegistration({
        optionsJSON: registerResponse.options,
      })

      // Step 3: Complete registration with backend
      return await svc.completePasskeyRegistration(
        request.name,
        registerResponse.registrationToken,
        credential
      )
    },
    onSuccess: async () => {
      // Invalidate all 2FA queries to refresh status and passkey list
      await queryClient.invalidateQueries({ queryKey: twoFactorQueryKeys.all })
    },
  })
}

/**
 * Hook for verifying with a passkey during login
 */
export function useVerifyPasskey(service?: ITwoFactorService) {
  const queryClient = useQueryClient()
  const authStore = useAuthStore()

  return useMutation({
    mutationFn: async () => {
      const svc = service ?? twoFactorService
      const twoFactorToken = authStore.twoFactorToken
      if (!twoFactorToken) {
        throw new Error('No pending 2FA token — start from the login form')
      }

      // Step 1: Get verification options from backend
      const verifyResponse = await svc.verifyPasskey(twoFactorToken)

      // Step 2: Start WebAuthn authentication ceremony
      const credential = await startAuthentication({
        optionsJSON: verifyResponse.options,
      })

      // Step 3: Complete verification with backend
      return await svc.completePasskeyVerification(
        twoFactorToken,
        verifyResponse.challengeToken,
        credential
      )
    },
    onSuccess: async (data) => {
      if (data.verified && data.accessToken) {
        // Store the access token (refresh token is an HttpOnly cookie)
        authStore.setToken(data.accessToken)
        // Clear 2FA token
        authStore.clearTwoFactorToken()
        // Invalidate all 2FA queries to refresh status
        await queryClient.invalidateQueries({ queryKey: twoFactorQueryKeys.all })
      }
    },
  })
}

/**
 * Hook for deleting a passkey
 */
export function useDeletePasskey(service?: ITwoFactorService) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (passkeyId: string) => {
      return (service ?? twoFactorService).deletePasskey(passkeyId)
    },
    onSuccess: async () => {
      // Invalidate all 2FA queries to refresh status and passkey list
      await queryClient.invalidateQueries({ queryKey: twoFactorQueryKeys.all })
    },
  })
}
