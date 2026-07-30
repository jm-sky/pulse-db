import './css/style.css'

import { VueQueryPlugin } from '@tanstack/vue-query'
import { QueryClient } from '@tanstack/vue-query'
import { vTooltip } from 'floating-vue'
import { createPinia } from 'pinia'
import { createApp } from 'vue'
import { i18n } from '@/i18n'
import { bootstrapAuth } from '@/modules/auth/composables/useAuthBootstrap'
import App from './App.vue'
import router from './router'
import { config } from './shared/config/config'
import { initSentry } from './shared/services/sentry'
import { initializeStores, setHtmlLangAttribute } from './shared/utils/appInit'
import { setupChunkLoadErrorHandler } from './shared/utils/chunkLoadError'
import { loadRecaptchaScript } from './shared/utils/recaptcha'
import 'floating-vue/dist/style.css'

// Set page title from app config
if (typeof document !== 'undefined') {
  document.title = config.app.name
}

// Load reCAPTCHA script early (non-blocking)
if (config.recaptcha.enabled) {
  loadRecaptchaScript().catch(console.error)
}

const app = createApp(App)
const pinia = createPinia()

// Create query client with default configuration
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
})

app.use(pinia)
app.use(router)
app.use(VueQueryPlugin, { queryClient })
app.use(i18n)
app.directive('tooltip', vTooltip)

// Initialize Sentry (must be after router is registered)
initSentry(app, router)

// Set HTML lang attribute based on initial locale
setHtmlLangAttribute(i18n)

// Setup global error handler for chunk loading errors
setupChunkLoadErrorHandler(i18n)

// Kick off the silent session restore (from the HttpOnly refresh cookie) as
// early as possible, in parallel with mounting. authGuard awaits the same
// memoized promise before evaluating requiresAuth on the first navigation —
// see useAuthBootstrap.ts for why that has to happen in the guard, not here.
bootstrapAuth()

app.mount('#app')

// H5 FIX: Initialize stores asynchronously after mount to avoid blocking main thread
// This loads data from localStorage without blocking initial UI render
initializeStores().catch((error) => {
  console.error('Failed to initialize stores:', error)
})
