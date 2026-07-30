// modules/auth/types/user.type.ts
import type { TDateTime, TULID } from '@/shared/types/base.type'

export interface User {
  id: TULID
  name: string
  email: string
  avatarUrl?: string
  isActive: boolean
  isAdmin: boolean
  isOwner: boolean
  isPremium: boolean
  isEmailVerified: boolean
  emailVerifiedAt?: TDateTime | null
  createdAt: TDateTime
  preferredTwoFactorMethod?: 'totp' | 'webauthn' | null
}

export interface LoginCredentials {
  email: string
  password: string
  recaptchaToken?: string | null
}

export interface RegisterCredentials {
  name: string
  email: string
  password: string
  passwordConfirmation: string
  recaptchaToken?: string | null
}

export interface ForgotPasswordData {
  email: string
  recaptchaToken?: string | null
}

export interface ResetPasswordData {
  email: string
  token: string
  password: string
  passwordConfirmation: string
}

export interface ChangePasswordData {
  currentPassword: string
  password: string
  passwordConfirmation: string
}

export interface AuthResponse {
  user: User
  accessToken: string
  tokenType: string
  expiresIn: number
  requiresEmailVerification: boolean
}

export interface TwoFactorRequiredResponse {
  requiresTwoFactor: true
  twoFactorToken: string
  methods: string[] // ["totp", "webauthn"]
  preferredMethod: string | null
  allowBackupCodes: boolean
  expiresAt: string // ISO datetime string
}

export type LoginResponse = AuthResponse | TwoFactorRequiredResponse

export interface RefreshTokenResponse {
  accessToken: string
  tokenType: string
  expiresIn: number
}

export interface MessageResponse {
  message: string
}

export interface RegisterResponse extends MessageResponse {
  email?: string
}

export interface OAuthAuthUrlResponse {
  authUrl: string
  state: string
}

export interface OAuthCallbackRequest {
  code: string
  state: string
  recaptchaToken?: string | null
}
