import { apiClient } from '@/shared/services/apiClient'
import type { IAdminUser } from '../types/admin.types'
import type { TUUID } from '@/shared/types/base.type'

class AdminApiService {
  async getUsers(skip = 0, limit = 100): Promise<IAdminUser[]> {
    const response = await apiClient.get<IAdminUser[]>('/admin/users', {
      params: { skip, limit },
    })
    return response.data
  }

  async getUser(id: TUUID): Promise<IAdminUser> {
    const response = await apiClient.get<IAdminUser>(`/admin/users/${id}`)
    return response.data
  }

  async updateUser(id: TUUID, data: { role?: 'user' | 'admin'; name?: string; email?: string; isActive?: boolean }): Promise<IAdminUser> {
    const response = await apiClient.patch<IAdminUser>(`/admin/users/${id}`, data)
    return response.data
  }

  async deleteUser(id: TUUID): Promise<void> {
    await apiClient.delete(`/admin/users/${id}`)
  }
}

export const adminApiService = new AdminApiService()
