/**
 * App Initialization Utilities
 */

import type { I18n } from 'vue-i18n'

function getCurrentLocale(i18n: I18n): string {
  return typeof i18n.global.locale === 'string' ? i18n.global.locale : i18n.global.locale.value
}

/**
 * Set HTML lang attribute based on current i18n locale
 */
export function setHtmlLangAttribute(i18n: I18n): void {
  if (typeof document === 'undefined') {
    return
  }
  const currentLocale = getCurrentLocale(i18n)
  document.documentElement.setAttribute('lang', currentLocale)
}

/**
 * Initialize stores asynchronously to avoid blocking main thread
 */
export async function initializeStores(): Promise<void> {
  // No stores to initialize at this point
}
