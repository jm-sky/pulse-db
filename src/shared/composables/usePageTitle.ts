// shared/composables/usePageTitle.ts

import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { config } from '@/shared/config/config'

/**
 * Composable for managing page titles
 *
 * Provides functionality to set dynamic page titles with i18n support.
 * Titles are formatted as: "{Page Title} | {App Name}"
 *
 * @example
 * ```ts
 * const { setTitle, resetTitle } = usePageTitle()
 *
 * // Set static title
 * setTitle('navigation.dashboard')
 *
 * // Set dynamic title with parameters
 * setTitle('dashboard.title', { name: 'PulseDB' })
 *
 * // Reset to route meta title
 * resetTitle()
 * ```
 */
export function usePageTitle() {
  const route = useRoute()
  const { t } = useI18n()

  /**
   * Set page title from i18n key with optional parameters
   *
   * @param key - i18n translation key
   * @param params - Optional parameters for i18n interpolation or direct name override
   */
  const setTitle = (key: string, params?: Record<string, string>) => {
    if (typeof document === 'undefined') return

    // If params contains 'name', use it directly in the title format: "{name} | {App Name}"
    if (params?.name) {
      document.title = `${params.name} | ${config.app.name}`
      return
    }

    const title = params ? t(key, params) : t(key)
    document.title = `${title} | ${config.app.name}`
  }

  /**
   * Reset page title to route meta title (if available)
   * Falls back to app name if no meta.title is set
   */
  const resetTitle = () => {
    if (typeof document === 'undefined') return

    const metaTitle = route.meta.title as string | undefined
    if (metaTitle) {
      const title = t(metaTitle)
      document.title = `${title} | ${config.app.name}`
    } else {
      document.title = config.app.name
    }
  }

  /**
   * Set title from route meta automatically
   * This is called by the router guard, but can be used manually
   */
  const setTitleFromRoute = () => {
    resetTitle()
  }

  return {
    setTitle,
    resetTitle,
    setTitleFromRoute,
  }
}

