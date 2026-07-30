import { USER_STORAGE_KEY } from '@/shared/config/config'
import type { IUser } from '../types/user.types'

export function loadFromStorage(): IUser | null {
  const stored = localStorage.getItem(USER_STORAGE_KEY)
  if (stored) {
    try {
      return JSON.parse(stored)
    } catch (error) {
      console.error('Error loading user from storage:', error)
    }
  }
  return null
}
