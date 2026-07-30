import { onMounted, onUnmounted } from 'vue'

/**
 * Composable to handle chunk loading errors that occur after deployment
 * When a new version is deployed, old chunks are removed, causing ChunkLoadError
 * This composable shows a notification to the user prompting them to refresh
 */
export function useChunkLoadErrorHandler() {
  const handleError = (event: ErrorEvent) => {
    const error = event.error

    // Check if it's a chunk load error
    const isChunkLoadError =
      error?.name === 'ChunkLoadError' ||
      error?.message?.includes('Failed to fetch dynamically imported module') ||
      error?.message?.includes('Importing a module script failed') ||
      (error?.message?.includes('fetch') && error?.message?.includes('chunk'))

    if (isChunkLoadError) {
      // Prevent default error handling
      event.preventDefault()

      // Show user-friendly message
      // Using confirm instead of alert to give user choice
      const shouldRefresh = window.confirm(
        'A new version of the application is available. The page needs to be reloaded to continue.\n\nClick OK to reload now, or Cancel to continue (some features may not work).'
      )

      if (shouldRefresh) {
        window.location.reload()
      }
    }
  }

  onMounted(() => {
    window.addEventListener('error', handleError)
  })

  onUnmounted(() => {
    window.removeEventListener('error', handleError)
  })
}
