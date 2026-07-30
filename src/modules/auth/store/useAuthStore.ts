// modules/auth/store/useAuthStore.ts
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { useUserStore } from '@/modules/user/store/useUserStore'
import type { User } from '@/modules/auth/types/user.type'

const TWO_FACTOR_TOKEN_KEY = 'vbr_2fa_token'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  // In-memory only — the refresh token lives in an HttpOnly cookie the SPA
  // never sees, and the access token is no longer persisted to localStorage
  // (XSS hardening). Session survives reload via a silent refresh on boot,
  // see useAuthBootstrap.
  const token = ref<string | null>(null)
  const twoFactorToken = ref<string | null>(localStorage.getItem(TWO_FACTOR_TOKEN_KEY))
  const twoFactorMethods = ref<string[]>([]) // Available 2FA methods from login response
  const preferredTwoFactorMethod = ref<string | null>(null) // Preferred method from login response

  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const isTwoFactorPending = computed(() => !!twoFactorToken.value && !token.value)

  const setToken = (newToken: string) => {
    token.value = newToken
    // Clear 2FA token when access token is set (2FA verification completed)
    if (newToken) {
      clearTwoFactorToken()
    }
  }

  const setTwoFactorToken = (newToken: string, methods?: string[], preferredMethod?: string | null) => {
    twoFactorToken.value = newToken
    if (newToken) {
      localStorage.setItem(TWO_FACTOR_TOKEN_KEY, newToken)
      if (methods) {
        twoFactorMethods.value = methods
      }
      if (preferredMethod !== undefined) {
        preferredTwoFactorMethod.value = preferredMethod
      }
    } else {
      localStorage.removeItem(TWO_FACTOR_TOKEN_KEY)
      twoFactorMethods.value = []
      preferredTwoFactorMethod.value = null
    }
  }

  const setUser = (newUser: User | null) => {
    user.value = newUser

    // Sync with userStore for profile page
    if (newUser) {
      const userStore = useUserStore()
      userStore.setUser({
        id: newUser.id,
        name: newUser.name,
        email: newUser.email,
        avatarUrl: newUser.avatarUrl,
        isAdmin: newUser.isAdmin,
        isOwner: newUser.isOwner,
        isPremium: newUser.isPremium,
        createdAt: newUser.createdAt,
        updatedAt: new Date().toISOString(),
      })
    }
  }

  const clearToken = () => {
    token.value = null
  }

  const clearTwoFactorToken = () => {
    twoFactorToken.value = null
    localStorage.removeItem(TWO_FACTOR_TOKEN_KEY)
  }

  const clearUser = () => {
    user.value = null
    // Reset userStore to default user on logout
    const userStore = useUserStore()
    userStore.initializeDefaultUser()
  }

  const logout = () => {
    clearToken()
    clearTwoFactorToken()
    clearUser()
  }

  return {
    user,
    token,
    twoFactorToken,
    twoFactorMethods,
    preferredTwoFactorMethod,
    isAuthenticated,
    isTwoFactorPending,
    setToken,
    clearToken,
    setTwoFactorToken,
    clearTwoFactorToken,
    setUser,
    clearUser,
    logout,
  }
})
