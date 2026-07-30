export interface IFeatureLimit {
  id: string
  role: 'user' | 'premium' | 'admin' | 'owner'
  aiLimit: number | null
  storageLimitBytes: number
  description: string | null
  createdAt: string
  updatedAt: string
}

export interface IFeatureLimitCreate {
  role: 'user' | 'premium' | 'admin' | 'owner'
  aiLimit: number | null
  storageLimitBytes: number
  description?: string | null
}

export interface IFeatureLimitUpdate {
  aiLimit?: number | null
  storageLimitBytes?: number
  description?: string | null
}

