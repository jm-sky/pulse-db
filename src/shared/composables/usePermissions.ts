import { computed } from 'vue'
import { useAuthStore } from '@/modules/auth/store/useAuthStore'
import { useUserStore } from '@/modules/user/store/useUserStore'
import type { User } from '@/modules/auth/types/user.type'

/**
 * Composable for centralized permission logic.
 * Provides permission checks and utilities for role-based access control.
 */
export function usePermissions() {
  const authStore = useAuthStore()
  const userStore = useUserStore()

  /**
   * Get current user from authStore or userStore
   */
  const user = computed<User | null>(() => {
    return authStore.user ?? (userStore.user ? {
      id: userStore.user.id,
      name: userStore.user.name,
      email: userStore.user.email,
      avatarUrl: userStore.user.avatarUrl,
      isActive: true,
      isAdmin: userStore.user.isAdmin ?? false,
      isOwner: userStore.user.isOwner ?? false,
      isPremium: userStore.user.isPremium ?? false,
      isEmailVerified: true,
      createdAt: userStore.user.createdAt ?? new Date().toISOString(),
    } : null)
  })

  /**
   * Check if user has admin role
   */
  const isAdmin = computed<boolean>(() => {
    return user.value?.isAdmin ?? false
  })

  /**
   * Check if user has owner role
   */
  const isOwner = computed<boolean>(() => {
    return user.value?.isOwner ?? false
  })

  /**
   * Check if user has premium role
   */
  const isPremium = computed<boolean>(() => {
    return user.value?.isPremium ?? false
  })

  /**
   * Check if user has admin or owner role (for admin panel access)
   */
  const canAccessAdminPanel = computed<boolean>(() => {
    return isAdmin.value || isOwner.value
  })

  /**
   * Check if user has premium or higher role (Premium, Admin, or Owner)
   * Used for AI features and image search
   */
  const canUsePremiumFeatures = computed<boolean>(() => {
    return isPremium.value || isAdmin.value || isOwner.value
  })

  /**
   * Check if user is authenticated
   */
  const isAuthenticated = computed<boolean>(() => {
    return authStore.isAuthenticated
  })

  /**
   * Get user role as string
   */
  const userRole = computed<string>(() => {
    if (isOwner.value) return 'Owner'
    if (isAdmin.value) return 'Administrator'
    if (isPremium.value) return 'Premium User'
    return 'User'
  })

  return {
    user,
    isAdmin,
    isOwner,
    isPremium,
    canAccessAdminPanel,
    canUsePremiumFeatures,
    isAuthenticated,
    userRole,
  }
}
