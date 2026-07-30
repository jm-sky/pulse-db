// shared/i18n/config/i18n.ts

import { createI18n } from 'vue-i18n'
import { config, LOCALE_STORAGE_KEY, type SupportedLocale } from '@/shared/config/config'
import en from '../locales/en'
import pl from '../locales/pl'
import { getPolishPluralizationRule } from './getPolishPluralizationRule'
import type { I18n, I18nOptions } from 'vue-i18n'

export const SUPPORTED_LOCALES: SupportedLocale[] = ['en', 'pl']

export const LOCALE_LABELS: Record<SupportedLocale, string> = {
  en: 'English',
  pl: 'Polski',
}

/**
 * Detects preferred locale from browser settings
 * @param browserLanguages - Array of browser language preferences
 * @returns Preferred locale if supported, otherwise undefined
 */
export const getPreferredLocale = (browserLanguages: readonly string[]): SupportedLocale | undefined => {
  for (const lang of browserLanguages) {
    // Extract language code (e.g., 'en' from 'en-US')
    const languageCode = lang.split('-')[0]?.toLowerCase()

    if (languageCode && SUPPORTED_LOCALES.includes(languageCode as SupportedLocale)) {
      return languageCode as SupportedLocale
    }
  }

  return undefined
}

/**
 * Get stored locale, browser preferred locale, or default from config
 * Automatically saves detected browser locale to localStorage if not already stored
 */
const getStoredLocale = (): SupportedLocale => {
  // 1. Check localStorage first
  const stored = localStorage.getItem(LOCALE_STORAGE_KEY)
  if (stored && SUPPORTED_LOCALES.includes(stored as SupportedLocale)) {
    return stored as SupportedLocale
  }

  // 2. Check browser preferred language
  const browserLanguages = navigator.languages.length > 0 ? navigator.languages : [navigator.language]
  const preferred = getPreferredLocale(browserLanguages)
  if (preferred) {
    // Save detected locale to localStorage for future visits
    localStorage.setItem(LOCALE_STORAGE_KEY, preferred)
    return preferred
  }

  // 3. Use default from config
  const defaultLocale = config.i18n.defaultLocale
  // Optionally save default to localStorage (or leave empty for browser detection on next visit)
  return defaultLocale
}

// Default i18n configuration
export const defaultI18nOptions: I18nOptions<{ message: typeof en }> = {
  legacy: false, // Use Composition API mode
  locale: getStoredLocale(),
  fallbackLocale: config.i18n.fallbackLocale,
  messages: {
    en,
    pl,
  },
  // In Composition API mode (legacy: false), use 'pluralRules' instead of 'pluralizationRules'
  pluralRules: {
    pl: getPolishPluralizationRule,
  },
  globalInjection: true,
  missingWarn: import.meta.env.DEV,
  fallbackWarn: import.meta.env.DEV,
}

/**
 * Create i18n instance with custom options
 * @param options - Custom i18n options to override defaults
 */
export function createI18nInstance(options?: Partial<I18nOptions>): I18n {
  return createI18n({
    ...defaultI18nOptions,
    ...options,
  })
}

/**
 * Default i18n instance for the app
 */
export const i18n = createI18nInstance()
