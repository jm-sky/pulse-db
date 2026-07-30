import type {
  AuthenticationResponseJSON,
  PublicKeyCredentialCreationOptionsJSON,
  PublicKeyCredentialRequestOptionsJSON,
  RegistrationResponseJSON,
} from '@simplewebauthn/browser'
import type { TDateTime, TULID } from '@/shared/types/base.type'

// TOTP Types
export interface TotpSetup {
  secret: string // Secret key for generating codes
  qrCode: string // Data URL for QR code (or qrCodeUri)
  qrCodeUri?: string // QR code URI (alternative to qrCode)
  backupCodes: string[] // Backup codes for one-time use
  setupToken: string // Token for verifying setup
  expiresAt?: string // Expiration date
}

export interface TotpVerify {
  code: string // 6-digit code from authenticator app
}

export interface TotpStatus {
  enabled: boolean
  createdAt?: TDateTime
  lastUsedAt?: TDateTime
}

// WebAuthn Types
export interface Passkey {
  id: TULID // Credential ID
  name: string // User-given name (e.g., "iPhone", "Laptop")
  createdAt: TDateTime
  lastUsedAt?: TDateTime
}

export interface WebAuthnRegisterRequest {
  name: string // Passkey name
}

export interface WebAuthnRegisterResponse {
  options: PublicKeyCredentialCreationOptionsJSON
  registrationToken: string
  expiresAt: string
}

export interface WebAuthnVerifyRequest {
  credentialId?: string // Optional credential ID to use for verification
}

export interface WebAuthnVerifyResponse {
  options: PublicKeyCredentialRequestOptionsJSON
  challengeToken: string
  expiresAt: string
}

export interface WebAuthnStatus {
  enabled: boolean
  passkeys: Passkey[]
}

// Combined Types
export interface TwoFactorStatus {
  totp: TotpStatus
  webauthn: WebAuthnStatus
  required: boolean // Whether 2FA is required (global setting)
}

export interface UpdatePreferredMethodRequest {
  preferredMethod: 'totp' | 'webauthn' | null
}

export interface TwoFactorVerifyResponse {
  verified: boolean
  method: 'totp' | 'webauthn'
  accessToken: string // New access token with tfaVerified=true in payload
  tokenType?: string // Usually "Bearer"
  expiresIn?: number // Token expiration time in seconds
}

// JWT Payload Extension (for decoding JWT)
export interface TwoFactorJWTPayload {
  tfaPending?: boolean // Whether 2FA verification is required
  tfaVerified?: boolean // Whether 2FA has been verified
  tfaMethod?: 'totp' | 'webauthn' | null // 2FA method
}

// Service interface
export interface ITwoFactorService {
  // TOTP
  setupTotp(): Promise<TotpSetup>
  verifyTotp(setupToken: string, code: string): Promise<{ verified: boolean }>
  verifyTotpLogin(twoFactorToken: string, code: string): Promise<TwoFactorVerifyResponse>
  disableTotp(password: string): Promise<void>
  getTotpStatus(): Promise<TotpStatus>

  // WebAuthn
  registerPasskey(request: WebAuthnRegisterRequest): Promise<WebAuthnRegisterResponse>
  completePasskeyRegistration(
    name: string,
    registrationToken: string,
    credential: RegistrationResponseJSON
  ): Promise<Passkey>
  verifyPasskey(twoFactorToken: string): Promise<WebAuthnVerifyResponse>
  completePasskeyVerification(
    twoFactorToken: string,
    challengeToken: string,
    credential: AuthenticationResponseJSON
  ): Promise<TwoFactorVerifyResponse>
  listPasskeys(): Promise<Passkey[]>
  deletePasskey(passkeyId: string): Promise<void>
  getWebAuthnStatus(): Promise<WebAuthnStatus>

  // Combined
  getTwoFactorStatus(): Promise<TwoFactorStatus>
  updatePreferredMethod(request: UpdatePreferredMethodRequest): Promise<{ preferredMethod: 'totp' | 'webauthn' | null }>
}
