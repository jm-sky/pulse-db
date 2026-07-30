// shared/config/config.ts

// Supported locales type (defined here to avoid cyclic dependencies)
export type SupportedLocale = 'en' | 'pl'

export const config = {
  app: {
    id: import.meta.env.VITE_APP_ID ?? 'pulse-db',
    name: import.meta.env.VITE_APP_NAME ?? 'PulseDB',
    description: import.meta.env.VITE_APP_DESCRIPTION ?? 'Database performance diagnostics for PostgreSQL and SQL Server.',
    // Public repo URL for the footer GitHub link; set to null to hide the link
    githubUrl: 'https://github.com/jm-sky/pulse-db' as string | null,
  },
  i18n: {
    defaultLocale: (import.meta.env.VITE_DEFAULT_LOCALE ?? 'en') as SupportedLocale,
    fallbackLocale: (import.meta.env.VITE_FALLBACK_LOCALE ?? 'en') as SupportedLocale,
  },
  contact: {
    companyName: import.meta.env.VITE_COMPANY_NAME ?? 'DEV Made IT',
    companyWebsite: import.meta.env.VITE_COMPANY_WEBSITE ?? 'https://dev-made.it',
    email: import.meta.env.VITE_CONTACT_EMAIL ?? 'contact@dev-made.it',
    officialCompanyName: import.meta.env.VITE_OFFICIAL_COMPANY_NAME ?? 'SAVA GROUP sp. z o.o.',
    officialCompanyWebsite: import.meta.env.VITE_OFFICIAL_COMPANY_WEBSITE ?? 'https://sava-group.pl',
  },
  backend: {
    enabled: import.meta.env.VITE_ENABLE_BACKEND === 'true',
    baseUrl: import.meta.env.VITE_API_BASE_URL ?? '/api',
  },
  recaptcha: {
    siteKey: import.meta.env.VITE_GOOGLE_RECAPTCHA_SITE_KEY ?? '',
    enabled: !!import.meta.env.VITE_GOOGLE_RECAPTCHA_SITE_KEY,
  },
  oauth: {
    google: {
      clientId: import.meta.env.VITE_GOOGLE_OAUTH_CLIENT_ID ?? '',
      enabled: !!import.meta.env.VITE_GOOGLE_OAUTH_CLIENT_ID,
    },
    facebook: {
      clientId: import.meta.env.VITE_FACEBOOK_OAUTH_CLIENT_ID ?? '',
      enabled: !!import.meta.env.VITE_FACEBOOK_OAUTH_CLIENT_ID,
    },
    github: {
      clientId: import.meta.env.VITE_GITHUB_OAUTH_CLIENT_ID ?? '',
      enabled: !!import.meta.env.VITE_GITHUB_OAUTH_CLIENT_ID,
    },
  },
  features: {
    imageSearch: {
      enabled: import.meta.env.VITE_ENABLE_IMAGE_SEARCH === 'true',
    },
    ai: {
      enabled: import.meta.env.VITE_ENABLE_AI === 'true',
    },
    inlineEditing: {
      enabled: !(import.meta.env.VITE_ENABLE_INLINE_EDITING === 'false'),
    },
  },
  storage: {
    // Maximum file size for regular users (20 MB)
    maxFileSize: import.meta.env.VITE_MAX_FILE_SIZE ? parseInt(import.meta.env.VITE_MAX_FILE_SIZE) : 20 * 1024 * 1024,
    // Maximum file size for administrators (50 MB)
    maxFileSizeAdmin: import.meta.env.VITE_MAX_FILE_SIZE_ADMIN ? parseInt(import.meta.env.VITE_MAX_FILE_SIZE_ADMIN) : 50 * 1024 * 1024,
  },
  sentry: {
    dsn: import.meta.env.VITE_SENTRY_DSN ?? '',
    enabled: !!import.meta.env.VITE_SENTRY_DSN,
    environment: import.meta.env.VITE_SENTRY_ENVIRONMENT ?? import.meta.env.MODE ?? 'development',
    tracesSampleRate: import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE ? parseFloat(import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE) : 1.0,
    replaysSessionSampleRate: import.meta.env.VITE_SENTRY_REPLAYS_SESSION_SAMPLE_RATE ? parseFloat(import.meta.env.VITE_SENTRY_REPLAYS_SESSION_SAMPLE_RATE) : 0.1,
    replaysOnErrorSampleRate: import.meta.env.VITE_SENTRY_REPLAYS_ON_ERROR_SAMPLE_RATE ? parseFloat(import.meta.env.VITE_SENTRY_REPLAYS_ON_ERROR_SAMPLE_RATE) : 1.0,
  },
}

// osobna zmienna do użycia w localStorage / store
export const DARK_MODE_STORAGE_KEY = `${config.app.id}:dark-mode`
export const LOCALE_STORAGE_KEY = `${config.app.id}:locale`
export const SETTINGS_STORAGE_KEY = `${config.app.id}:settings`
export const CORE_SETTINGS_STORAGE_KEY = `${config.app.id}:core-settings`
export const USER_STORAGE_KEY = `${config.app.id}:user`
