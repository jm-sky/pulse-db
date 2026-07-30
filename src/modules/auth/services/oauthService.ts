// modules/auth/services/oauthService.ts
import { apiClient } from '@/shared/services/apiClient'

export interface OAuthConnection {
  id: string
  provider: string
  providerId: string
  email: string | null
  name: string | null
  avatarUrl: string | null
  createdAt: string
}

export interface OAuthConnectionsListResponse {
  connections: OAuthConnection[]
}

export interface MessageResponse {
  message: string
}

class OAuthService {
  /**
   * Get all OAuth connections for the current user
   */
  async getConnections(): Promise<OAuthConnection[]> {
    const response = await apiClient.get<OAuthConnectionsListResponse>('/auth/oauth/connections')
    return response.data.connections
  }

  /**
   * Delete an OAuth connection for the current user
   */
  async deleteConnection(provider: string): Promise<MessageResponse> {
    const response = await apiClient.delete<MessageResponse>(`/auth/oauth/connections/${provider}`)
    return response.data
  }
}

export const oauthService = new OAuthService()


