import { useBackend } from '@/shared/composables/useBackend'
import { USER_STORAGE_KEY } from '@/shared/config/config'
import type { IUpdateUserDto, IUser } from '../types/user.types'
import { createDefaultUser } from '../utils/createDefaultUser'
import { userApiService } from './userApiService'

/**
 * User Service (LocalStorage implementation)
 * Handles user data operations using localStorage
 */
class UserLocalService {
  async getUser(): Promise<IUser> {
    const stored = localStorage.getItem(USER_STORAGE_KEY)
    if (stored) {
      try {
        return JSON.parse(stored)
      } catch (error) {
        console.error('Error loading user from storage:', error)
      }
    }

    // Initialize default user if none exists
    const defaultUser = createDefaultUser()
    await this.saveUser(defaultUser)
    return defaultUser
  }

  async updateUser(data: IUpdateUserDto): Promise<IUser> {
    const current = await this.getUser()
    const updated: IUser = {
      ...current,
      ...data,
      updatedAt: new Date().toISOString(),
    }
    await this.saveUser(updated)
    return updated
  }

  async saveUser(user: IUser): Promise<void> {
    try {
      localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user))
    } catch (error) {
      console.error('Error saving user to storage:', error)
      throw error
    }
  }
}

/**
 * User Service Factory
 *
 * Returns appropriate service based on backend status and authentication.
 * When backend is enabled AND user is authenticated, uses API service.
 * Otherwise, uses localStorage service.
 */
export const userService = () => {
  const { shouldUseAPI } = useBackend()
  const localService = new UserLocalService()

  if (shouldUseAPI.value) {
    // Wrap API service to sync localStorage as backup
    return {
      async getUser(): Promise<IUser> {
        try {
          // API call
          const user = await userApiService.getUser()
          // Save to localStorage as backup
          await localService.saveUser(user).catch(err => {
            console.warn('Failed to save user to localStorage backup:', err)
          })
          return user
        } catch (error) {
          // Fallback to localStorage
          console.warn('API failed, falling back to localStorage', error)
          return localService.getUser()
        }
      },
      async updateUser(data: IUpdateUserDto): Promise<IUser> {
        try {
          // API call - API has priority
          const user = await userApiService.updateUser(data)
          // Save to localStorage as backup
          await localService.saveUser(user).catch(err => {
            console.warn('Failed to save user to localStorage backup:', err)
          })
          return user
        } catch (error) {
          // Fallback to localStorage
          console.warn('API failed, falling back to localStorage', error)
          return localService.updateUser(data)
        }
      },
    }
  }

  // Offline mode or not authenticated - use localStorage
  console.log('userService: Using localStorage service (shouldUseAPI is false)')
  return localService
}

// Export local service instance for direct use
export const userLocalService = new UserLocalService()

