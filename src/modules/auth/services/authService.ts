// modules/auth/services/authService.ts
import { apiClient } from '@/shared/services/apiClient'
import type { IAuthService } from '@/modules/auth/types/auth.type'
import type {
  ChangePasswordData,
  ForgotPasswordData,
  LoginCredentials,
  LoginResponse,
  MessageResponse,
  OAuthAuthUrlResponse,
  OAuthCallbackRequest,
  RefreshTokenResponse,
  RegisterCredentials,
  RegisterResponse,
  ResetPasswordData,
  User,
} from '@/modules/auth/types/user.type'

class AuthService implements IAuthService {
  async login(credentials: LoginCredentials): Promise<LoginResponse> {
    const response = await apiClient.post<LoginResponse>('/auth/login', credentials)
    return response.data
  }

  async register(credentials: RegisterCredentials): Promise<RegisterResponse> {
    const response = await apiClient.post<RegisterResponse>('/auth/register', credentials)
    return response.data
  }

  async logout(): Promise<void> {
    await apiClient.post('/auth/logout')
  }

  async refreshAccessToken(): Promise<RefreshTokenResponse> {
    // No body — the refresh token is sent automatically via the HttpOnly cookie
    const response = await apiClient.post<RefreshTokenResponse>('/auth/refresh')
    return response.data
  }

  async forgotPassword(data: ForgotPasswordData): Promise<MessageResponse> {
    const response = await apiClient.post<MessageResponse>('/auth/forgot-password', data)
    return response.data
  }

  async resetPassword(data: ResetPasswordData): Promise<MessageResponse> {
    const response = await apiClient.post<MessageResponse>('/auth/reset-password', data)
    return response.data
  }

  async changePassword(data: ChangePasswordData): Promise<MessageResponse> {
    const response = await apiClient.post<MessageResponse>('/auth/change-password', data)
    return response.data
  }

  async getCurrentUser(): Promise<User> {
    // Token is sent via apiClient interceptor (Authorization header)
    const response = await apiClient.get<User & { avatarUrl?: string }>('/auth/me')
    // Map avatarUrl from backend to avatar in frontend
    return {
      ...response.data,
      avatarUrl: response.data.avatarUrl,
    }
  }

  async deleteAccount(confirmation: string, password?: string): Promise<MessageResponse> {
    const response = await apiClient.delete<MessageResponse>('/auth/account', {
      data: { confirmation, password },
    })
    return response.data
  }

  async verifyEmail(token: string): Promise<MessageResponse> {
    const response = await apiClient.post<MessageResponse>('/auth/email/verify', { token })
    return response.data
  }

  async resendVerification(email: string): Promise<MessageResponse> {
    const response = await apiClient.post<MessageResponse>('/auth/email/resend', { email })
    return response.data
  }

  async getOAuthAuthUrl(provider: string): Promise<OAuthAuthUrlResponse> {
    const response = await apiClient.post<OAuthAuthUrlResponse>('/auth/oauth/auth-url', { provider })
    return response.data
  }

  async oauthCallback(provider: string, data: OAuthCallbackRequest): Promise<LoginResponse> {
    const response = await apiClient.post<LoginResponse>(`/auth/oauth/callback/${provider}`, data)
    return response.data
  }
}

export const authService = new AuthService()

