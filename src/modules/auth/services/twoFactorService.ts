import { apiClient } from '@/shared/services/apiClient'
// modules/auth/services/twoFactorService.ts
import type {
  AuthenticationResponseJSON,
  RegistrationResponseJSON,
} from '@simplewebauthn/browser'
import type {
  ITwoFactorService,
  Passkey,
  TotpSetup,
  TotpStatus,
  TwoFactorStatus,
  TwoFactorVerifyResponse,
  UpdatePreferredMethodRequest,
  WebAuthnRegisterRequest,
  WebAuthnRegisterResponse,
  WebAuthnStatus,
  WebAuthnVerifyResponse,
} from '@/modules/auth/types/twoFactor.type'

class TwoFactorService implements ITwoFactorService {
  // TOTP Methods
  async setupTotp(): Promise<TotpSetup> {
    const response = await apiClient.post<{
      qrCodeUri: string
      secret: string
      backupCodes: string[]
      setupToken: string
      expiresAt: string
    }>('/two-factor/totp/initiate')

    // Generate QR code data URL from URI
    const QRCode = await import('qrcode')
    const qrCode = await QRCode.default.toDataURL(response.data.qrCodeUri)

    return {
      secret: response.data.secret,
      qrCode,
      qrCodeUri: response.data.qrCodeUri,
      backupCodes: response.data.backupCodes,
      setupToken: response.data.setupToken,
      expiresAt: response.data.expiresAt,
    }
  }

  async verifyTotp(setupToken: string, code: string): Promise<{ verified: boolean }> {
    const response = await apiClient.post<{ verified: boolean }>('/two-factor/totp/verify', {
      setupToken,
      code,
    })
    return response.data
  }

  async verifyTotpLogin(twoFactorToken: string, code: string): Promise<TwoFactorVerifyResponse> {
    const response = await apiClient.post<TwoFactorVerifyResponse>('/two-factor/totp/verify-login', {
      twoFactorToken,
      code,
    })
    return response.data
  }

  async disableTotp(password: string): Promise<void> {
    await apiClient.post('/two-factor/totp/disable', { password })
  }

  async getTotpStatus(): Promise<TotpStatus> {
    const response = await apiClient.get<{
      isEnabled: boolean
      createdAt?: string
      lastVerifiedAt?: string
    }>('/two-factor/totp/status')
    return {
      enabled: response.data.isEnabled,
      createdAt: response.data.createdAt,
      lastUsedAt: response.data.lastVerifiedAt,
    }
  }

  // WebAuthn Methods
  async registerPasskey(request: WebAuthnRegisterRequest): Promise<WebAuthnRegisterResponse> {
    const response = await apiClient.post<WebAuthnRegisterResponse>(
      '/two-factor/webauthn/register/initiate',
      request
    )
    return response.data
  }

  async completePasskeyRegistration(
    name: string,
    registrationToken: string,
    credential: RegistrationResponseJSON
  ): Promise<Passkey> {
    const response = await apiClient.post<Passkey>('/two-factor/webauthn/register/complete', {
      name,
      registrationToken,
      credential,
    })
    return response.data
  }

  async verifyPasskey(twoFactorToken: string): Promise<WebAuthnVerifyResponse> {
    const response = await apiClient.post<WebAuthnVerifyResponse>('/two-factor/webauthn/authenticate/initiate', {
      twoFactorToken,
    })
    return response.data
  }

  async completePasskeyVerification(
    twoFactorToken: string,
    challengeToken: string,
    credential: AuthenticationResponseJSON
  ): Promise<TwoFactorVerifyResponse> {
    const response = await apiClient.post<TwoFactorVerifyResponse>('/two-factor/webauthn/authenticate/complete', {
      twoFactorToken,
      challengeToken,
      credential,
    })
    return response.data
  }

  async listPasskeys(): Promise<Passkey[]> {
    const response = await apiClient.get<{ passkeys: Passkey[], total: number }>(
      '/two-factor/webauthn/passkeys'
    )
    return response.data.passkeys
  }

  async deletePasskey(passkeyId: string): Promise<void> {
    await apiClient.delete(`/two-factor/webauthn/passkeys/${passkeyId}`)
  }

  async getWebAuthnStatus(): Promise<WebAuthnStatus> {
    const response = await apiClient.get<WebAuthnStatus>('/two-factor/webauthn/status')
    return response.data
  }

  // Combined Methods
  async getTwoFactorStatus(): Promise<TwoFactorStatus> {
    const response = await apiClient.get<TwoFactorStatus>('/two-factor/status')
    return response.data
  }

  async updatePreferredMethod(
    request: UpdatePreferredMethodRequest
  ): Promise<{ preferredMethod: 'totp' | 'webauthn' | null }> {
    const response = await apiClient.patch<{ preferredMethod: 'totp' | 'webauthn' | null }>(
      '/two-factor/preferred-method',
      request
    )
    return response.data
  }
}

export const twoFactorService = new TwoFactorService()
