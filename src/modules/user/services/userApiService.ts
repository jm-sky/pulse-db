// modules/user/services/userApiService.ts
import { apiClient } from '@/shared/services/apiClient'
import type { IUpdateUserDto, IUser } from '../types/user.types'

/**
 * Backend API response type (from /me endpoint)
 */
interface UserResponse {
  id: string
  email: string
  name: string
  role?: string
  isAdmin?: boolean
  isOwner?: boolean
  isPremium?: boolean
  isActive?: boolean
  isEmailVerified?: boolean
  avatarUrl?: string
  createdAt: string
  updatedAt: string
  features?: {
    ai: {
      enabled: boolean
      limit: number | null
    }
    storage: {
      limit: number
    }
  }
}

/**
 * Backend API response type for public user profile
 */
interface PublicUserResponse {
  id: string
  name: string
  avatarUrl?: string
  isAdmin: boolean
  isOwner?: boolean
  isPremium?: boolean
  email?: string
  emailPublic: boolean
}

/**
 * User API Service
 * Handles API calls for user data when backend is enabled and user is authenticated
 */
class UserApiService {
  /**
   * Get current user from API
   */
  async getUser(): Promise<IUser> {
    const response = await apiClient.get<UserResponse>('/users/me')
    return this.mapToIUser(response.data)
  }

  /**
   * Update current user profile
   */
  async updateUser(data: IUpdateUserDto): Promise<IUser> {
    const response = await apiClient.patch<UserResponse>('/users/me', data)
    return this.mapToIUser(response.data)
  }

  /**
   * Get public user profile by user ID
   */
  async getPublicUser(userId: string): Promise<IUser> {
    const response = await apiClient.get<PublicUserResponse>(`/users/${userId}/public`)
    return this.mapPublicUserToIUser(response.data)
  }

  /**
   * Map backend UserResponse to frontend IUser
   */
  private mapToIUser(response: UserResponse): IUser {
    return {
      id: response.id,
      name: response.name,
      email: response.email,
      avatarUrl: response.avatarUrl,
      isAdmin: response.isAdmin ?? response.role === 'admin',
      isOwner: response.isOwner ?? response.role === 'owner',
      isPremium: response.isPremium ?? response.role === 'premium',
      createdAt: response.createdAt,
      updatedAt: response.updatedAt,
      features: response.features,
    }
  }

  /**
   * Map backend PublicUserResponse to frontend IUser
   */
  private mapPublicUserToIUser(response: PublicUserResponse): IUser {
    return {
      id: response.id,
      name: response.name,
      email: response.email ?? '',
      avatarUrl: response.avatarUrl,
      isAdmin: response.isAdmin,
      isOwner: response.isOwner,
      isPremium: response.isPremium,
      emailPublic: response.emailPublic,
      createdAt: '', // Not provided in public profile
      updatedAt: '', // Not provided in public profile
    }
  }
}

export const userApiService = new UserApiService()

