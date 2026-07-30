/**
 * Chunk Load Error Handler
 *
 * Utility function to handle chunk loading errors that occur after deployment.
 * When a new version is deployed, old chunks are removed, causing ChunkLoadError.
 * This function shows a user-friendly message prompting them to refresh.
 */

import type { I18n } from 'vue-i18n'

/**
 * Check if an error is a chunk load error
 *
 * @param error - Error object to check
 * @returns true if error is a chunk load error
 */
export function isChunkLoadError(error: unknown): boolean {
  const errorObj = error as { name?: string; message?: string }
  return (
    errorObj?.name === 'ChunkLoadError' ||
    Boolean(errorObj?.message?.includes('Failed to fetch dynamically imported module')) ||
    Boolean(errorObj?.message?.includes('Importing a module script failed')) ||
    (Boolean(errorObj?.message?.includes('fetch')) && Boolean(errorObj?.message?.includes('chunk')))
  )
}

/**
 * Get current locale from i18n instance
 *
 * @param i18n - Vue i18n instance
 * @returns Current locale string
 */
function getCurrentLocale(i18n: I18n): string {
  return typeof i18n.global.locale === 'string' ? i18n.global.locale : i18n.global.locale.value
}

/**
 * Handle chunk load error event
 * Shows a user-friendly message with i18n support and prompts for page reload
 *
 * @param event - Error event
 * @param i18n - Vue i18n instance for locale detection
 */
export function handleChunkLoadError(event: ErrorEvent, i18n: I18n): void {
  const error = event.error

  if (isChunkLoadError(error)) {
    // Prevent default error handling
    event.preventDefault()

    // Get current locale
    const currentLocale = getCurrentLocale(i18n)
    const isPolish = currentLocale === 'pl'

    // Show user-friendly message with confirm dialog
    const title = isPolish ? 'Nowa wersja aplikacji' : 'New Version Available'
    const message = isPolish
      ? 'Aplikacja została zaktualizowana. Aby kontynuować, należy odświeżyć stronę.'
      : 'A new version of the application is available. The page needs to be reloaded to continue.'
    const description = isPolish ? 'Zapisz swoją pracę przed odświeżeniem.' : 'Please save your work before reloading.'

    const shouldRefresh = window.confirm(`${title}\n\n${message}\n\n${description}`)

    if (shouldRefresh) {
      window.location.reload()
    }
  }
}

/**
 * Setup global chunk load error handler
 * Registers a window error event listener for chunk load errors
 *
 * @param i18n - Vue i18n instance for locale detection
 * @returns Cleanup function to remove the event listener
 */
export function setupChunkLoadErrorHandler(i18n: I18n): () => void {
  const errorHandler = (event: ErrorEvent) => {
    handleChunkLoadError(event, i18n)
  }

  window.addEventListener('error', errorHandler)

  // Return cleanup function
  return () => {
    window.removeEventListener('error', errorHandler)
  }
}

