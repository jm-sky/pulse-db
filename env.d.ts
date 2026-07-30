/// <reference types="vite/client" />

declare const __APP_VERSION__: string
declare const __BUILD_DATE__: string

interface ImportMetaEnv {
  readonly VITE_APP_NAME?: string
  readonly VITE_APP_ID?: string
  readonly VITE_APP_DESCRIPTION?: string
  readonly VITE_API_URL?: string
  readonly VITE_API_BASE_URL?: string
  readonly VITE_ENABLE_BACKEND?: string
  readonly VITE_AUTH_LOGIN_PATH?: string
  readonly VITE_AUTH_REGISTER_PATH?: string
  readonly VITE_AUTH_FORGOT_PASSWORD_PATH?: string
  readonly VITE_AUTH_RESET_PASSWORD_PATH?: string
  readonly VITE_AUTH_CHANGE_PASSWORD_PATH?: string
  readonly VITE_AUTH_TWO_FACTOR_SETUP_PATH?: string
  readonly VITE_AUTH_TWO_FACTOR_VERIFY_PATH?: string
  readonly VITE_AUTH_VERIFY_EMAIL_PATH?: string
  readonly VITE_AUTH_DASHBOARD_PATH?: string
  readonly VITE_DEFAULT_LOCALE?: string
  readonly VITE_FALLBACK_LOCALE?: string
  readonly VITE_CONTACT_EMAIL?: string
  readonly VITE_API_PROXY_URL?: string
  readonly VITE_PORT?: string
  readonly VITE_SENTRY_DSN?: string
  readonly VITE_SENTRY_ENVIRONMENT?: string
  readonly VITE_SENTRY_TRACES_SAMPLE_RATE?: string
  readonly VITE_SENTRY_REPLAYS_SESSION_SAMPLE_RATE?: string
  readonly VITE_SENTRY_REPLAYS_ON_ERROR_SAMPLE_RATE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare module 'qrcode'

declare module 'virtual:pwa-register/vue' {
  import type { Ref } from 'vue'

  export interface RegisterSWOptions {
    immediate?: boolean
    onRegistered?: (registration: ServiceWorkerRegistration | undefined) => void
    onRegisterError?: (error: unknown) => void
    onNeedRefresh?: () => void
    onOfflineReady?: () => void
  }

  export function useRegisterSW(options?: RegisterSWOptions): {
    needRefresh: Ref<boolean>
    offlineReady: Ref<boolean>
    updateServiceWorker: (reloadPage?: boolean) => Promise<void>
  }
}
