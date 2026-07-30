import type { TDateTime, TUUID } from '@/shared/types/base.type'

export type TUserRole = 'user' | 'admin'

export interface IAdminUser {
  id: TUUID
  name: string
  email: string
  avatarUrl?: string
  isActive: boolean
  isAdmin: boolean
  isOwner: boolean
  isEmailVerified: boolean
  emailVerifiedAt?: TDateTime | null
  createdAt: TDateTime
  updatedAt: TDateTime
}
