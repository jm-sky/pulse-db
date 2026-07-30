import type { SupportedLocale } from '@/shared/i18n'

export type Theme = 'light' | 'dark'

export type ImageProcessingMode = 'high_quality' | 'balanced' | 'storage_saver'

export interface Settings {
  darkMode: boolean
  locale: SupportedLocale
  profilePublic: boolean
  emailPublic: boolean
  imageProcessingMode?: ImageProcessingMode | null
}

export interface UpdateSettingsData {
  darkMode?: boolean
  locale?: SupportedLocale
  profilePublic?: boolean
  emailPublic?: boolean
  imageProcessingMode?: ImageProcessingMode | null
}

export interface ISettingsService {
  getSettings(): Promise<Settings>
  updateSettings(data: UpdateSettingsData): Promise<Settings>
}
