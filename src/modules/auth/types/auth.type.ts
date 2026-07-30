import type { ChangePasswordData, ForgotPasswordData, LoginCredentials, LoginResponse, MessageResponse, RefreshTokenResponse, RegisterCredentials, RegisterResponse, ResetPasswordData, User } from './user.type'

export interface IAuthService {
  login(credentials: LoginCredentials): Promise<LoginResponse>
  register(credentials: RegisterCredentials): Promise<RegisterResponse>
  logout(): Promise<void>
  refreshAccessToken(): Promise<RefreshTokenResponse>
  forgotPassword(data: ForgotPasswordData): Promise<MessageResponse>
  resetPassword(data: ResetPasswordData): Promise<MessageResponse>
  changePassword(data: ChangePasswordData): Promise<MessageResponse>
  getCurrentUser(): Promise<User>
  deleteAccount(confirmation: string, password?: string): Promise<MessageResponse>
  verifyEmail(token: string): Promise<MessageResponse>
  resendVerification(email: string): Promise<MessageResponse>
}
