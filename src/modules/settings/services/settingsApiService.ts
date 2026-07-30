// modules/settings/services/settingsApiService.ts
import { apiClient } from '@/shared/services/apiClient'
import type { ISettingsService, Settings, UpdateSettingsData } from '@/modules/settings/types/settings.type'

/**
 * Sanitize update data: convert undefined to null for optional fields
 * Backend expects null instead of undefined for optional fields
 */
function sanitizeUpdateData(data: UpdateSettingsData): UpdateSettingsData {
  const sanitized: UpdateSettingsData = {}

  if (data.darkMode !== undefined) {
    sanitized.darkMode = data.darkMode
  }
  if (data.locale !== undefined) {
    sanitized.locale = data.locale
  }
  if (data.profilePublic !== undefined) {
    sanitized.profilePublic = data.profilePublic
  }
  if (data.emailPublic !== undefined) {
    sanitized.emailPublic = data.emailPublic
  }
  if (data.imageProcessingMode !== undefined) {
    sanitized.imageProcessingMode = data.imageProcessingMode ?? null
  }

  return sanitized
}

class SettingsApiService implements ISettingsService {
  async getSettings(): Promise<Settings> {
    const response = await apiClient.get<Settings>('/me/settings')
    return response.data
  }

  async updateSettings(data: UpdateSettingsData): Promise<Settings> {
    const sanitized = sanitizeUpdateData(data)
    const response = await apiClient.patch<Settings>('/me/settings', sanitized)
    return response.data
  }
}

export const settingsApiService = new SettingsApiService()
