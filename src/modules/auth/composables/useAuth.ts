/* eslint-disable @typescript-eslint/no-explicit-any */
// modules/auth/composables/useAuth.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed } from 'vue'
import { getAuthConfig } from '@/modules/auth/config/auth.config'
import { authService } from '@/modules/auth/services/authService'
import { useAuthStore } from '@/modules/auth/store/useAuthStore'
import {
  authMutationRetryFunction,
  authQueryKeys,
  authRetryFunction
} from '@/modules/auth/utils/queryUtils'
import type { IAuthService } from '@/modules/auth/types/auth.type'
import type {
  ChangePasswordData,
  ForgotPasswordData,
  LoginCredentials,
  LoginResponse,
  RegisterCredentials,
  ResetPasswordData,
  User
} from '@/modules/auth/types/user.type'

/**
 * Hook for fetching current user data
 * Automatically refetches when token changes
 * Uses placeholderData from authStore to avoid blocking critical path
 */
export function useCurrentUser(service?: IAuthService) {
  const authStore = useAuthStore()
  const config = getAuthConfig()

  return useQuery({
    queryKey: authQueryKeys.me(),
    queryFn: () => (service ?? authService).getCurrentUser(),
    enabled: !!authStore.token, // Only fetch if user is authenticated
    staleTime: config.query.staleTime,
    retry: authRetryFunction,
    // Use cached user data from store as placeholder to avoid blocking critical path
    // Query will still execute in background, but component can render immediately
    placeholderData: authStore.user ?? undefined,
    // Don't refetch on mount if we have cached data (unless stale)
    refetchOnMount: !authStore.user,
  })
}

/**
 * Hook for user login with automatic user data fetching
 */
export function useLogin(service?: IAuthService) {
  const authStore = useAuthStore()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (credentials: LoginCredentials) => {
      const response = await (service ?? authService).login(credentials)
      // Check if 2FA is required
      if ('requiresTwoFactor' in response && response.requiresTwoFactor) {
        // Store 2FA token and methods instead of access token
        authStore.setTwoFactorToken(
          response.twoFactorToken,
          response.methods,
          response.preferredMethod
        )
        // Don't set access token - user needs to complete 2FA first
      } else if ('accessToken' in response) {
        // Normal login response - set access token (refresh token is an HttpOnly cookie)
        authStore.setToken(response.accessToken)
        // Set user from login response (map avatarUrl to avatar)
        if (response.user) {
          authStore.setUser({
            ...response.user,
            avatarUrl: (response.user as any).avatarUrl || response.user.avatarUrl,
          })
        }
      }
      return response
    },
    onSuccess: async (data: LoginResponse) => {
      // If it's a normal auth response (not 2FA required), set user and invalidate queries
      if ('accessToken' in data && 'user' in data) {
        // Set user from login response (map avatarUrl to avatar)
        authStore.setUser({
          ...data.user,
          avatarUrl: (data.user as any).avatarUrl ?? data.user.avatarUrl,
        })

        // Invalidate and refetch user data to ensure consistency
        if (!data.requiresEmailVerification) {
          await queryClient.invalidateQueries({ queryKey: authQueryKeys.me() })

  
        }
      }
      // If 2FA is required, don't set user or invalidate queries yet
      // The user will be set after 2FA verification completes
    },
    onError: () => {
      // Clear auth state on error
      authStore.logout()
    },
    retry: authMutationRetryFunction,
  })
}

/**
 * Hook for user registration with automatic user data fetching
 */
export function useRegister(service?: IAuthService) {
  return useMutation({
    mutationFn: (credentials: RegisterCredentials) => (service ?? authService).register(credentials),
    onError: () => {
      const authStore = useAuthStore()
      authStore.logout()
    },
    retry: authMutationRetryFunction,
  })
}

/**
 * Hook for user logout with cache cleanup
 */
export function useLogout(service?: IAuthService) {
  const authStore = useAuthStore()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => (service ?? authService).logout(),
    onSuccess: () => {
      // Clear all auth-related cache
      queryClient.removeQueries({ queryKey: authQueryKeys.all })

      // Clear auth store
      authStore.logout()
    },
    onError: () => {
      // Even if logout fails on server, clear local state
      queryClient.removeQueries({ queryKey: authQueryKeys.all })
      authStore.logout()
    },
    retry: authMutationRetryFunction,
  })
}

/**
 * Hook for forgot password
 */
export function useForgotPassword(service?: IAuthService) {
  return useMutation({
    mutationFn: (data: ForgotPasswordData) => (service ?? authService).forgotPassword(data),
    retry: authMutationRetryFunction,
  })
}

/**
 * Hook for reset password
 */
export function useResetPassword(service?: IAuthService) {
  return useMutation({
    mutationFn: (data: ResetPasswordData) => (service ?? authService).resetPassword(data),
    retry: authMutationRetryFunction,
  })
}

/**
 * Hook for change password
 */
export function useChangePassword(service?: IAuthService) {
  return useMutation({
    mutationFn: (data: ChangePasswordData) => (service ?? authService).changePassword(data),
    retry: authMutationRetryFunction,
  })
}

/**
 * Hook for delete account
 */
export function useDeleteAccount(service?: IAuthService) {
  const authStore = useAuthStore()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ confirmation, password }: { confirmation: string; password?: string }) =>
      (service ?? authService).deleteAccount(confirmation, password),
    onSuccess: () => {
      // Clear all auth-related cache
      queryClient.removeQueries({ queryKey: authQueryKeys.all })

      // Clear auth store
      authStore.logout()
    },
    onError: () => {
      // Even if deletion fails, we keep the user logged in
      // (in case of temporary network issues)
    },
    retry: authMutationRetryFunction,
  })
}

/**
 * Main auth composable with TanStack Query integration
 */
export function useAuth(service?: IAuthService) {
  const authStore = useAuthStore()
  const queryClient = useQueryClient()

  // Queries
  const currentUserQuery = useCurrentUser(service)

  // Mutations
  const loginMutation = useLogin(service)
  const registerMutation = useRegister(service)
  const logoutMutation = useLogout(service)
  const forgotPasswordMutation = useForgotPassword(service)
  const resetPasswordMutation = useResetPassword(service)
  const changePasswordMutation = useChangePassword(service)
  const deleteAccountMutation = useDeleteAccount(service)
  const verifyEmailMutation = useMutation({
    mutationFn: (token: string) => (service ?? authService).verifyEmail(token),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: authQueryKeys.me() })
    },
    retry: authMutationRetryFunction,
  })
  const resendVerificationMutation = useMutation({
    mutationFn: (email: string) => (service ?? authService).resendVerification(email),
    retry: authMutationRetryFunction,
  })

  // Computed values (keep refs reactive)
  const user = computed<User | null>(() => currentUserQuery.data.value ?? authStore.user)
  const isAuthenticated = computed<boolean>(() => !!authStore.token && !!user.value)
  const isEmailVerified = computed<boolean>(() => user.value?.isEmailVerified ?? false)
  const isLoading = currentUserQuery.isLoading
  const isError = currentUserQuery.isError

  // Helper function to refresh user data
  const fetchUser = () => {
    return queryClient.invalidateQueries({ queryKey: authQueryKeys.me() })
  }

  // Helper function to update user data optimistically
  const updateUser = (updater: (oldUser: User | null) => User | null) => {
    queryClient.setQueryData(authQueryKeys.me(), updater)
    authStore.setUser(updater(authStore.user))
  }

  return {
    // Data
    user,
    isAuthenticated,
    isEmailVerified,
    isLoading,
    isError,

    // Queries
    currentUserQuery,

    // Actions
    login: loginMutation.mutateAsync,
    register: registerMutation.mutateAsync,
    logout: logoutMutation.mutateAsync,
    forgotPassword: forgotPasswordMutation.mutateAsync,
    resetPassword: resetPasswordMutation.mutateAsync,
    changePassword: changePasswordMutation.mutateAsync,
    deleteAccount: deleteAccountMutation.mutateAsync,
    fetchUser,

    // Mutation states
    isLoggingIn: loginMutation.isPending,
    isRegistering: registerMutation.isPending,
    isLoggingOut: logoutMutation.isPending,
    isForgotPasswordLoading: forgotPasswordMutation.isPending,
    isResetPasswordLoading: resetPasswordMutation.isPending,
    isChangePasswordLoading: changePasswordMutation.isPending,
    isDeletingAccount: deleteAccountMutation.isPending,
    verifyEmail: verifyEmailMutation.mutateAsync,
    resendVerification: resendVerificationMutation.mutateAsync,
    isVerifyingEmail: verifyEmailMutation.isPending,
    isResendingVerification: resendVerificationMutation.isPending,

    // Helpers
    updateUser,
  }
}
