import { apiClient } from '@/shared/services/apiClient'
import type { IFeatureLimit, IFeatureLimitCreate, IFeatureLimitUpdate } from '../types/limits.types'

interface FeatureLimitResponse {
  id: string
  role: string
  ai_limit: number | null
  storage_limit_bytes: number
  description: string | null
  created_at: string
  updated_at: string
}

function mapToIFeatureLimit(response: FeatureLimitResponse): IFeatureLimit {
  return {
    id: response.id,
    role: response.role as 'user' | 'premium' | 'admin' | 'owner',
    aiLimit: response.ai_limit,
    storageLimitBytes: response.storage_limit_bytes,
    description: response.description,
    createdAt: response.created_at,
    updatedAt: response.updated_at,
  }
}

function mapToRequest(data: IFeatureLimitCreate | IFeatureLimitUpdate): Record<string, unknown> {
  if ('role' in data) {
    // Create request
    return {
      role: data.role,
      ai_limit: data.aiLimit,
      storage_limit_bytes: data.storageLimitBytes,
      description: data.description,
    }
  }
  // Update request
  const result: Record<string, unknown> = {}
  if (data.aiLimit !== undefined) result.ai_limit = data.aiLimit
  if (data.storageLimitBytes !== undefined) result.storage_limit_bytes = data.storageLimitBytes
  if (data.description !== undefined) result.description = data.description
  return result
}

class LimitsApiService {
  async getLimits(): Promise<IFeatureLimit[]> {
    const response = await apiClient.get<FeatureLimitResponse[]>('/feature-limits')
    return response.data.map(mapToIFeatureLimit)
  }

  async getLimitByRole(role: string): Promise<IFeatureLimit> {
    const response = await apiClient.get<FeatureLimitResponse>(`/feature-limits/${role}`)
    return mapToIFeatureLimit(response.data)
  }

  async createLimit(data: IFeatureLimitCreate): Promise<IFeatureLimit> {
    const response = await apiClient.post<FeatureLimitResponse>('/feature-limits', mapToRequest(data))
    return mapToIFeatureLimit(response.data)
  }

  async updateLimit(role: string, data: IFeatureLimitUpdate): Promise<IFeatureLimit> {
    const response = await apiClient.patch<FeatureLimitResponse>(`/feature-limits/${role}`, mapToRequest(data))
    return mapToIFeatureLimit(response.data)
  }

  async deleteLimit(role: string): Promise<void> {
    await apiClient.delete(`/feature-limits/${role}`)
  }
}

export const limitsApiService = new LimitsApiService()

