import { useAuthStore } from '@/modules/auth/store/useAuthStore'
import { useBackend } from '@/shared/composables/useBackend'
import { CORE_SETTINGS_STORAGE_KEY, LOCALE_STORAGE_KEY, SETTINGS_STORAGE_KEY, type SupportedLocale } from '@/shared/config/config'
import type { ISettingsService, Settings, UpdateSettingsData } from '../types/settings.type'
import { settingsApiService } from './settingsApiService'

/**
 * Settings Service (LocalStorage implementation)
 * Handles core application settings: locale, dark mode
 * Implements ISettingsService interface for localStorage-based operations.
 */
class SettingsLocalService implements ISettingsService {
  private static readonly STORAGE_KEY = CORE_SETTINGS_STORAGE_KEY
  private static readonly OLD_STORAGE_KEY = SETTINGS_STORAGE_KEY // For migration

  /**
   * Migrate from old storage format if needed
   */
  private migrateFromOldStorage(): Partial<Settings> | null {
    const oldStored = localStorage.getItem(SettingsLocalService.OLD_STORAGE_KEY)
    if (!oldStored) return null

    try {
      const oldSettings = JSON.parse(oldStored)
      return {
        locale: oldSettings.locale,
        darkMode: oldSettings.darkMode,
      }
    } catch {
      return null
    }
  }

  /**
   * Load core settings from localStorage
   * LOCALE_STORAGE_KEY is always the source of truth for locale
   */
  async getSettings(): Promise<Settings> {
    const stored = localStorage.getItem(SettingsLocalService.STORAGE_KEY)
    let settings: Partial<Settings> = {}

    if (stored) {
      try {
        settings = JSON.parse(stored)
      } catch (error) {
        console.error('Error loading core settings from storage:', error)
      }
    } else {
      // Try to migrate from old storage
      const migrated = this.migrateFromOldStorage()
      if (migrated) {
        settings = migrated
        // Save to new location
        this.saveToStorage({
          locale: migrated.locale ?? 'en',
          darkMode: migrated.darkMode ?? false,
          profilePublic: false,
          emailPublic: false,
        })
      }
    }

    // LOCALE_STORAGE_KEY is always the source of truth for locale
    const localeFromStorage = localStorage.getItem(LOCALE_STORAGE_KEY)
    const locale: SupportedLocale = (localeFromStorage && (localeFromStorage === 'en' || localeFromStorage === 'pl'))
      ? localeFromStorage as SupportedLocale
      : (settings.locale ?? 'en')

    return Promise.resolve({
      locale,
      darkMode: settings.darkMode ?? false,
      profilePublic: settings.profilePublic ?? false,
      emailPublic: settings.emailPublic ?? false,
      imageProcessingMode: settings.imageProcessingMode ?? 'balanced',
    })
  }

  /**
   * Update core settings
   * Note: This saves to localStorage only.
   * For proper i18n sync, use useLocale().setLocale() in composables.
   */
  async updateSettings(data: UpdateSettingsData): Promise<Settings> {
    const current = await this.getSettings()
    const updated: Settings = {
      locale: data.locale ?? current.locale,
      darkMode: data.darkMode ?? current.darkMode,
      profilePublic: data.profilePublic ?? current.profilePublic,
      imageProcessingMode: data.imageProcessingMode !== undefined ? data.imageProcessingMode : current.imageProcessingMode,
      emailPublic: data.emailPublic ?? current.emailPublic,
    }

    await this.saveToStorage(updated)
    return Promise.resolve(updated)
  }

  /**
   * Save core settings to localStorage (private helper)
   * LOCALE_STORAGE_KEY is always the source of truth for locale
   */
  private async saveToStorage(settings: Settings): Promise<void> {
    try {
      // Save locale to LOCALE_STORAGE_KEY (source of truth)
      // Note: This should be synced via useLocale().setLocale() for proper i18n sync
      // This is just for localStorage persistence
      localStorage.setItem(LOCALE_STORAGE_KEY, settings.locale)
        localStorage.setItem(SettingsLocalService.STORAGE_KEY, JSON.stringify({
          locale: settings.locale,
          darkMode: settings.darkMode,
          profilePublic: settings.profilePublic ?? false,
          emailPublic: settings.emailPublic ?? false,
          imageProcessingMode: settings.imageProcessingMode ?? 'balanced',
        }))
      return Promise.resolve()
    } catch (error) {
      console.error('Error saving core settings to storage:', error)
      return Promise.reject(error)
    }
  }
}

/**
 * Settings Service (Hybrid implementation)
 * When backend is enabled, uses API calls.
 * When backend is disabled, uses localStorage.
 * Implements ISettingsService interface.
 */
class SettingsService implements ISettingsService {
  private localService = new SettingsLocalService()

  private get isBackendEnabled() {
    const { isBackendEnabled } = useBackend()
    return isBackendEnabled.value
  }

  private get isAuthenticated(): boolean {
    // Check if user has an in-memory access token (simple check, no need to decode)
    return !!useAuthStore().token
  }

  async getSettings(): Promise<Settings> {
    // Only use API if backend is enabled AND user is authenticated
    if (this.isBackendEnabled && this.isAuthenticated) {
      try {
        // API call
        return await settingsApiService.getSettings()
      } catch (error) {
        // Fallback to localStorage
        console.warn('API failed, falling back to localStorage', error)
        return this.localService.getSettings()
      }
    }

    // Offline mode or not authenticated - use localStorage
    return this.localService.getSettings()
  }

  async updateSettings(data: UpdateSettingsData): Promise<Settings> {
    // Only use API if backend is enabled AND user is authenticated
    if (this.isBackendEnabled && this.isAuthenticated) {
      try {
        // API call - API has priority
        const settings = await settingsApiService.updateSettings(data)
        // Save to localStorage as backup
        // Note: locale is saved to LOCALE_STORAGE_KEY by localService
        // and synced via useLocale().setLocale() in composable (useUpdateSettings)
        await this.localService.updateSettings({
          locale: settings.locale,
          darkMode: settings.darkMode,
          profilePublic: settings.profilePublic,
          emailPublic: settings.emailPublic,
        })
        return settings
      } catch (error) {
        // Fallback to localStorage
        console.warn('API failed, falling back to localStorage', error)
        return this.localService.updateSettings(data)
      }
    }

    // Offline mode or not authenticated - use localStorage
    return this.localService.updateSettings(data)
  }
}

/**
 * Settings Service wrapper (for backward compatibility)
 * Provides static methods for backward compatibility
 */
export class SettingsServiceStatic {
  private static localService = new SettingsLocalService()

  /**
   * Load core settings from localStorage (static method for backward compatibility)
   * LOCALE_STORAGE_KEY is always the source of truth for locale
   */
  static loadFromStorage(): Settings {
    // Synchronous version for backward compatibility
    const stored = localStorage.getItem(CORE_SETTINGS_STORAGE_KEY)
    let settings: Partial<Settings> = {}

    if (stored) {
      try {
        settings = JSON.parse(stored)
      } catch (error) {
        console.error('Error loading core settings from storage:', error)
      }
    }

    // LOCALE_STORAGE_KEY is always the source of truth for locale
    const localeFromStorage = localStorage.getItem(LOCALE_STORAGE_KEY)
    const locale: SupportedLocale = (localeFromStorage && (localeFromStorage === 'en' || localeFromStorage === 'pl'))
      ? localeFromStorage as SupportedLocale
      : (settings.locale ?? 'en')

    return {
      locale,
      darkMode: settings.darkMode ?? false,
      profilePublic: settings.profilePublic ?? false,
      emailPublic: settings.emailPublic ?? false,
    }
  }

  /**
   * Update core settings (static method for backward compatibility)
   * Note: For proper i18n sync, use useLocale().setLocale() instead
   */
  static updateSettings(current: Settings, updates: UpdateSettingsData): Settings {
    const updated: Settings = {
      locale: updates.locale ?? current.locale,
      darkMode: updates.darkMode ?? current.darkMode,
      profilePublic: updates.profilePublic ?? current.profilePublic,
      emailPublic: updates.emailPublic ?? current.emailPublic,
    }

    try {
      // Save locale to LOCALE_STORAGE_KEY (source of truth)
      localStorage.setItem(LOCALE_STORAGE_KEY, updated.locale)
        localStorage.setItem(CORE_SETTINGS_STORAGE_KEY, JSON.stringify({
          locale: updated.locale,
          darkMode: updated.darkMode,
          profilePublic: updated.profilePublic,
          emailPublic: updated.emailPublic,
        }))
    } catch (error) {
      console.error('Error saving core settings to storage:', error)
    }

    return updated
  }

  /**
   * Get instance of local service (for interface implementation)
   */
  static getLocalService(): ISettingsService {
    return this.localService
  }
}

// Export instance for direct use (hybrid implementation)
export const settingsService = new SettingsService()

// Export local service instance for direct use
export const settingsLocalService = new SettingsLocalService()

// Export static class for backward compatibility (renamed to avoid conflict)
export { SettingsServiceStatic as SettingsService }
