import type { TUUID } from '@/shared/types/base.type'

export interface IAiFeatures {
  enabled: boolean
  limit: number | null // AI usage limit in USD (null = unlimited)
}

export interface IStorageFeatures {
  limit: number // Storage limit in bytes
}

export interface IUserFeatures {
  ai: IAiFeatures
  storage: IStorageFeatures
}

export interface IUser {
  id: TUUID
  name: string
  email: string
  avatarUrl?: string
  isAdmin?: boolean
  isOwner?: boolean
  isPremium?: boolean
  emailPublic?: boolean // Whether email is public (for public profiles)
  createdAt: string
  updatedAt: string
  features?: IUserFeatures // Only included in /me endpoint
}

export interface IUpdateUserDto {
  name?: string
  email?: string
  avatarUrl?: string
}

