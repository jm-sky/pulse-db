import { defineStore } from 'pinia'
import { computed, reactive } from 'vue'
import { USER_STORAGE_KEY } from '@/shared/config/config'
import type { IUpdateUserDto, IUser } from '../types/user.types'
import { createDefaultUser } from '../utils/createDefaultUser'
import { loadFromStorage } from './loadFromStorage'

function initializeUser(): IUser | null {
  const loaded = loadFromStorage()
  if (loaded) {
    return loaded
  }

  // Initialize default user if none exists
  const defaultUser = createDefaultUser()
  try {
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(defaultUser))
  } catch (error) {
    console.error('Error saving default user to storage:', error)
  }
  return defaultUser
}

export const useUserStore = defineStore('user', () => {
  const state = reactive<{ user: IUser | null }>({
    user: initializeUser(),
  })

  // Getters
  const getProfile = computed<IUser | null>(() => state.user)

  // Actions
  function setUser(user: IUser): void {
    state.user = user
    saveToStorage()
  }

  function initializeDefaultUser(): void {
    if (state.user) return // User already exists

    const defaultUser = createDefaultUser()
    setUser(defaultUser)
  }

  function updateUser(data: IUpdateUserDto): void {
    if (!state.user) {
      // If no user exists, initialize with default and update
      initializeDefaultUser()
    }

    if (!state.user) return

    state.user = {
      ...state.user,
      ...data,
      updatedAt: new Date().toISOString(),
    }
    saveToStorage()
  }

  function loadFromStorageAction(): void {
    state.user = loadFromStorage()
  }

  function saveToStorage(): void {
    try {
      if (state.user) {
        localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(state.user))
      } else {
        localStorage.removeItem(USER_STORAGE_KEY)
      }
    } catch (error) {
      console.error('Error saving user to storage:', error)
    }
  }

  return {
    // State - Pinia automatically exposes reactive properties
    user: computed(() => state.user),

    // Getters
    getProfile,

    // Actions
    setUser,
    initializeDefaultUser,
    updateUser,
    loadFromStorage: loadFromStorageAction,
    saveToStorage,
  }
})

